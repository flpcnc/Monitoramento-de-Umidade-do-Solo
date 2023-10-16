import machine
import dht
import time

# Pino conectado ao sensor de solo
pin_sensor_solo = machine.ADC(26)  # Substitua pelo número do pino correto no Raspberry Pi Pico
# Pino conectado ao sensor DHT22
pin_sensor_dht = machine.Pin(2)  # Substitua pelo número do pino correto no Raspberry Pi Pico

# Inicialize o objeto DHT
dht_sensor = dht.DHT22(pin_sensor_dht)

# Quantidade de amostras para cálculo da média
numero_amostras = 100  # Altere para a quantidade desejada de amostras

def coletar_media_sensor_solo(pin, num_amostras):
    somatoria = 0
    somatoria_temperatura = 0
    somatoria_umidade = 0

    for i in range(1, num_amostras + 1):
        leitura_sensor = pin.read_u16()
        tensao = (leitura_sensor / 65535) * 3.3  # Ajuste para a referência de 3.3V
        
        # Leitura do sensor DHT22
        dht_sensor.measure()
        temperatura = dht_sensor.temperature()
        umidade = dht_sensor.humidity()
        
        print("Sensor de Solo | Amostra {} | Leitura: {} | Tensão: {:.2f}V | Temperatura: {:.2f}°C | Umidade: {:.2f}%".format(i, leitura_sensor, tensao, temperatura, umidade))
        
        somatoria += leitura_sensor
        somatoria_temperatura += temperatura
        somatoria_umidade += umidade
        
        time.sleep(1)

    media_leitura = somatoria // num_amostras
    media_temperatura = somatoria_temperatura / num_amostras
    media_umidade = somatoria_umidade / num_amostras

    print("\nMédia de Leitura do Sensor de Solo: {}".format(media_leitura))
    print("Média de Temperatura do DHT22: {:.2f}°C".format(media_temperatura))
    print("Média de Umidade do DHT22: {:.2f}%".format(media_umidade))

    estado_solo = determinar_estado_solo(media_leitura)
    print("Estado do Solo: {}".format(estado_solo))

def determinar_estado_solo(leitura):
    threshold_umido = 25000  # Valor arbitrário para identificar solo úmido
    threshold_seco = 48000  # Valor arbitrário para identificar solo seco

    if leitura < threshold_umido:
        return "Úmido"
    elif leitura > threshold_seco:
        return "Seco"
    else:
        return "Intermediário"

def main():
    print("Leitura de Sensores - Raspberry Pi Pico\n")
    coletar_media_sensor_solo(pin_sensor_solo, numero_amostras)

if __name__ == "__main__":
    main()

