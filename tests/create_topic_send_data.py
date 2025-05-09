from kafka import KafkaProducer
import time

producer = KafkaProducer(bootstrap_servers=['rss-kafka-ingest:9092'])
topic = 'RSSTopic'

for i in range(1, 101):
    message = "Nachricht {}".format(i).encode('utf-8')
    producer.send(topic, message)
    print("Gesendet: {}".format(message))
    time.sleep(0.1)

producer.flush()
producer.close()
