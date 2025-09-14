import machine
import dht
import time
import os

# Configuração dos pinos
pin_sensor_solo = machine.ADC(26)  # Pino analógico para sensor de solo
pin_sensor_dht = machine.Pin(2)    # Pino digital para DHT22

# Inicializar sensor DHT22
dht_sensor = dht.DHT22(pin_sensor_dht)

# Configurações de calibração do sensor de solo
# IMPORTANTE: Calibre estes valores com seu sensor específico
VALOR_SOLO_SECO = 49525      # Leitura ADC quando solo está completamente seco
VALOR_SOLO_UMIDO = 20947     # Leitura ADC quando solo está saturado de água

# Configurações do modo híbrido (Deep Sleep)
MODO_DEEP_SLEEP = False       # True = modo bateria, False = modo desenvolvimento
TEMPO_COLETA_SEGUNDOS = 60   # Tempo coletando dados (1 minuto)
INTERVALO_SLEEP_MINUTOS = 15 # Tempo dormindo entre coletas (15 minutos)
INTERVALO_LEITURA = 2        # Segundos entre cada amostra durante coleta

# Configurações gerais
nome_arquivo_csv = "dados_sensores.csv"

def converter_para_porcentagem_umidade(leitura_adc):
    """
    Converte leitura ADC para porcentagem de umidade do solo
    0% = solo completamente seco
    100% = solo saturado de água
    """
    # Limitar valores dentro do range calibrado
    if leitura_adc >= VALOR_SOLO_SECO:
        return 0.0  # Solo seco
    elif leitura_adc <= VALOR_SOLO_UMIDO:
        return 100.0  # Solo saturado
    
    # Calcular porcentagem (invertido porque menor ADC = mais úmido)
    porcentagem = 100.0 * (VALOR_SOLO_SECO - leitura_adc) / (VALOR_SOLO_SECO - VALOR_SOLO_UMIDO)
    return round(porcentagem, 1)

def determinar_estado_solo_porcentagem(porcentagem_umidade):
    """
    Determina estado do solo baseado na porcentagem de umidade
    """
    if porcentagem_umidade >= 70:
        return "Úmido"
    elif porcentagem_umidade <= 30:
        return "Seco"
    else:
        return "Intermediário"

def criar_cabecalho_csv():
    """
    Cria arquivo CSV com cabeçalho se não existir
    """
    try:
        # Verificar se arquivo já existe
        with open(nome_arquivo_csv, 'r') as f:
            pass  # Arquivo existe, não fazer nada
    except OSError:
        # Arquivo não existe, criar com cabeçalho
        with open(nome_arquivo_csv, 'w') as f:
            f.write("timestamp,ciclo,duracao_coleta_s,num_amostras,leitura_adc_media,tensao_v_media,umidade_solo_pct,estado_solo,temperatura_c,umidade_ar_pct\n")
        print(f"Arquivo {nome_arquivo_csv} criado com cabeçalho.")

def salvar_dados_csv(timestamp, ciclo, duracao_coleta, num_amostras, leitura_adc_media, tensao_media, umidade_solo_pct, estado_solo, temperatura, umidade_ar):
    """
    Salva uma linha de dados consolidados no arquivo CSV
    """
    try:
        with open(nome_arquivo_csv, 'a') as f:
            linha = f"{timestamp},{ciclo},{duracao_coleta},{num_amostras},{leitura_adc_media},{tensao_media:.2f},{umidade_solo_pct},{estado_solo},{temperatura:.2f},{umidade_ar:.2f}\n"
            f.write(linha)
    except Exception as e:
        print(f"Erro ao salvar no CSV: {e}")

def obter_timestamp():
    """
    Retorna timestamp simples (segundos desde boot)
    Para timestamp real, seria necessário RTC ou conexão de rede
    """
    return time.ticks_ms() // 1000

def obter_contador_ciclos():
    """
    Lê/incrementa contador de ciclos salvo em arquivo
    """
    try:
        with open("contador_ciclos.txt", 'r') as f:
            ciclo = int(f.read().strip()) + 1
    except:
        ciclo = 1
    
    # Salvar novo valor
    try:
        with open("contador_ciclos.txt", 'w') as f:
            f.write(str(ciclo))
    except:
        pass
    
    return ciclo

def coletar_dados_periodo(duracao_segundos):
    """
    Coleta dados dos sensores durante um período específico
    Retorna médias consolidadas
    """
    print(f"🔄 Iniciando coleta por {duracao_segundos} segundos...")
    
    # Calcular quantas amostras cabem no período
    num_amostras = duracao_segundos // INTERVALO_LEITURA
    if num_amostras < 1:
        num_amostras = 1
    
    print(f"📊 Coletando {num_amostras} amostras com intervalo de {INTERVALO_LEITURA}s")
    
    # Variáveis para somatórias
    soma_leitura_adc = 0
    soma_temperatura = 0
    soma_umidade_ar = 0
    soma_umidade_solo = 0
    amostras_validas = 0
    
    inicio_coleta = time.ticks_ms()
    
    # Coletar amostras durante o período
    for i in range(1, num_amostras + 1):
        try:
            # Leitura do sensor de solo
            leitura_adc = pin_sensor_solo.read_u16()
            tensao = (leitura_adc / 65535) * 3.3
            umidade_solo_pct = converter_para_porcentagem_umidade(leitura_adc)
            estado_solo = determinar_estado_solo_porcentagem(umidade_solo_pct)
            
            # Leitura do sensor DHT22
            dht_sensor.measure()
            temperatura = dht_sensor.temperature()
            umidade_ar = dht_sensor.humidity()
            
            # Exibir dados na tela (modo compacto)
            print(f"  {i:2d}/{num_amostras} | {umidade_solo_pct:5.1f}% ({estado_solo}) | {temperatura:.1f}°C | {umidade_ar:.1f}%")
            
            # Somar para cálculo de médias
            soma_leitura_adc += leitura_adc
            soma_temperatura += temperatura
            soma_umidade_ar += umidade_ar
            soma_umidade_solo += umidade_solo_pct
            amostras_validas += 1
            
            time.sleep(INTERVALO_LEITURA)
            
        except Exception as e:
            print(f"  ❌ Erro na amostra {i}: {e}")
            continue
    
    fim_coleta = time.ticks_ms()
    duracao_real = (fim_coleta - inicio_coleta) // 1000
    
    # Calcular médias
    if amostras_validas > 0:
        media_leitura_adc = soma_leitura_adc // amostras_validas
        media_temperatura = soma_temperatura / amostras_validas
        media_umidade_ar = soma_umidade_ar / amostras_validas
        media_umidade_solo = soma_umidade_solo / amostras_validas
        media_tensao = (media_leitura_adc / 65535) * 3.3
        estado_medio_solo = determinar_estado_solo_porcentagem(media_umidade_solo)
    else:
        print("❌ Nenhuma amostra válida coletada!")
        return None
    
    return {
        'duracao_real': duracao_real,
        'amostras_validas': amostras_validas,
        'media_leitura_adc': media_leitura_adc,
        'media_tensao': media_tensao,
        'media_umidade_solo': media_umidade_solo,
        'estado_medio_solo': estado_medio_solo,
        'media_temperatura': media_temperatura,
        'media_umidade_ar': media_umidade_ar
    }

def entrar_deep_sleep(minutos):
    """
    Coloca o Raspberry Pi Pico em Deep Sleep por X minutos
    """
    if not MODO_DEEP_SLEEP:
        print(f"⏳ Modo desenvolvimento: aguardando {minutos} min sem Deep Sleep...")
        time.sleep(minutos * 60)
        return
    
    print(f"😴 Entrando em Deep Sleep por {minutos} minutos...")
    print("💡 Para acordar: pressione RESET ou desconecte/reconecte USB")
    
    # Configurar Deep Sleep
    milissegundos = minutos * 60 * 1000
    
    # No Raspberry Pi Pico, usamos machine.deepsleep()
    try:
        machine.deepsleep(milissegundos)
    except:
        # Fallback se deepsleep não estiver disponível
        print("⚠️  Deep Sleep não disponível, usando sleep normal...")
        time.sleep(minutos * 60)

def exibir_info_arquivo():
    """
    Exibe informações sobre o arquivo CSV salvo
    """
    try:
        stat = os.stat(nome_arquivo_csv)
        print(f"📁 Arquivo: {nome_arquivo_csv} | Tamanho: {stat[6]} bytes")
        
        # Contar linhas
        with open(nome_arquivo_csv, 'r') as f:
            linhas = sum(1 for linha in f)
        print(f"📊 Total de registros: {linhas - 1}")  # Menos o cabeçalho
        
    except Exception as e:
        print(f"❌ Erro ao obter informações do arquivo: {e}")

def main_modo_hibrido():
    """
    Função principal - modo híbrido com Deep Sleep
    """
    print("="*80)
    print("🌱 MONITOR DE UMIDADE - MODO HÍBRIDO (DEEP SLEEP)")
    print("="*80)
    print(f"⚙️  Configuração:")
    print(f"   - Solo seco: {VALOR_SOLO_SECO} ADC")
    print(f"   - Solo úmido: {VALOR_SOLO_UMIDO} ADC")
    print(f"   - Tempo de coleta: {TEMPO_COLETA_SEGUNDOS}s")
    print(f"   - Intervalo sleep: {INTERVALO_SLEEP_MINUTOS} min")
    print(f"   - Modo Deep Sleep: {'✅ Ativo' if MODO_DEEP_SLEEP else '❌ Desabilitado (desenvolvimento)'}")
    print(f"   - Arquivo: {nome_arquivo_csv}")
    print("="*80)
    
    # Criar arquivo CSV se não existir
    criar_cabecalho_csv()
    
    # Loop principal
    while True:
        try:
            # Obter número do ciclo
            ciclo = obter_contador_ciclos()
            timestamp = obter_timestamp()
            
            print(f"\n🔄 CICLO {ciclo} - Timestamp: {timestamp}")
            
            # Coletar dados durante o período especificado
            dados = coletar_dados_periodo(TEMPO_COLETA_SEGUNDOS)
            
            if dados:
                # Exibir resumo
                print(f"\n📊 RESUMO DO CICLO {ciclo}:")
                print(f"   Duração real: {dados['duracao_real']}s")
                print(f"   Amostras válidas: {dados['amostras_validas']}")
                print(f"   Umidade Solo: {dados['media_umidade_solo']:.1f}% ({dados['estado_medio_solo']})")
                print(f"   Temperatura: {dados['media_temperatura']:.1f}°C")
                print(f"   Umidade Ar: {dados['media_umidade_ar']:.1f}%")
                
                # Salvar no CSV
                salvar_dados_csv(
                    timestamp, ciclo, dados['duracao_real'], dados['amostras_validas'],
                    dados['media_leitura_adc'], dados['media_tensao'],
                    dados['media_umidade_solo'], dados['estado_medio_solo'],
                    dados['media_temperatura'], dados['media_umidade_ar']
                )
                
                print(f"✅ Dados salvos no CSV")
                
                # Exibir info do arquivo
                exibir_info_arquivo()
            
            # Entrar em Deep Sleep
            print(f"\n😴 Próximo ciclo em {INTERVALO_SLEEP_MINUTOS} minutos...")
            entrar_deep_sleep(INTERVALO_SLEEP_MINUTOS)
            
        except KeyboardInterrupt:
            print("\n⏹️  Monitoramento interrompido pelo usuário.")
            break
        except Exception as e:
            print(f"❌ Erro no ciclo {ciclo}: {e}")
            print("⏳ Aguardando 30s antes de tentar novamente...")
            time.sleep(30)

# Funções de calibração (mantidas iguais)
def calibrar_solo_seco():
    """
    Calibração específica para solo seco
    Execute esta função com o sensor em solo completamente seco
    """
    print("="*60)
    print("🌵 CALIBRAÇÃO SOLO SECO")
    print("="*60)
    print("INSTRUÇÕES:")
    print("1. Retire o sensor do solo/água")
    print("2. Deixe-o secar completamente ao ar livre")
    print("3. Ou coloque em solo completamente seco")
    print("4. Aguarde as 10 leituras...")
    print("-"*60)
    
    leituras = []
    for i in range(10):
        leitura = pin_sensor_solo.read_u16()
        tensao = (leitura / 65535) * 3.3
        leituras.append(leitura)
        print(f"Leitura {i+1:2d}: {leitura:5d} ADC | {tensao:.2f}V")
        time.sleep(1)
    
    media = sum(leituras) // len(leituras)
    print("-"*60)
    print(f"📊 RESULTADO SOLO SECO:")
    print(f"   Valor médio: {media} ADC")
    print(f"   Tensão média: {(media/65535)*3.3:.2f}V")
    print("-"*60)
    print(f"✅ COPIE ESTE VALOR:")
    print(f"   VALOR_SOLO_SECO = {media}")
    print("="*60)
    return media

def calibrar_solo_umido():
    """
    Calibração específica para solo úmido/saturado
    Execute esta função com o sensor em solo saturado de água
    """
    print("="*60)
    print("💧 CALIBRAÇÃO SOLO ÚMIDO")
    print("="*60)
    print("INSTRUÇÕES:")
    print("1. Coloque o sensor em solo bem molhado/saturado")
    print("2. Ou mergulhe a parte metálica em água")
    print("3. NÃO molhe a parte eletrônica!")
    print("4. Aguarde as 10 leituras...")
    print("-"*60)
    
    leituras = []
    for i in range(10):
        leitura = pin_sensor_solo.read_u16()
        tensao = (leitura / 65535) * 3.3
        leituras.append(leitura)
        print(f"Leitura {i+1:2d}: {leitura:5d} ADC | {tensao:.2f}V")
        time.sleep(1)
    
    media = sum(leituras) // len(leituras)
    print("-"*60)
    print(f"📊 RESULTADO SOLO ÚMIDO:")
    print(f"   Valor médio: {media} ADC")
    print(f"   Tensão média: {(media/65535)*3.3:.2f}V")
    print("-"*60)
    print(f"✅ COPIE ESTE VALOR:")
    print(f"   VALOR_SOLO_UMIDO = {media}")
    print("="*60)
    return media

def teste_calibracao():
    """
    Testa a calibração atual mostrando como ficaria a conversão
    """
    print("="*60)
    print("🧪 TESTE DA CALIBRAÇÃO ATUAL")
    print("="*60)
    print(f"Configuração atual:")
    print(f"- VALOR_SOLO_SECO = {VALOR_SOLO_SECO}")
    print(f"- VALOR_SOLO_UMIDO = {VALOR_SOLO_UMIDO}")
    print("-"*60)
    
    # Fazer algumas leituras de teste
    print("Fazendo 5 leituras de teste...")
    for i in range(5):
        leitura = pin_sensor_solo.read_u16()
        tensao = (leitura / 65535) * 3.3
        umidade_pct = converter_para_porcentagem_umidade(leitura)
        estado = determinar_estado_solo_porcentagem(umidade_pct)
        
        print(f"Teste {i+1}: {leitura:5d} ADC | {tensao:.2f}V | {umidade_pct:5.1f}% ({estado})")
        time.sleep(1)
    
    print("="*60)

if __name__ == "__main__":
    # Execução principal - modo híbrido com Deep Sleep
    main_modo_hibrido()