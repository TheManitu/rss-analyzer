from pipeline.topic_assignment import TopicAssigner

assigner = TopicAssigner()
cases = [
    ({"title":"Deep Learning Trends", "content":"...neuronale Netze, KI..."}, "Künstliche Intelligenz & Maschinelles Lernen"),
    ({"title":"AWS SageMaker Update", "content":"...aws ai, sagemaker, polly..."}, "Amazon AWS AI"),
    ({"title":"Unbekanntes Thema", "content":"Lorem ipsum dolor..."}, "Allgemein"),
]
for art, exp in cases:
    got = assigner.assign_topic(art['title'], art['content'])
    print(f"title={art['title']!r} → got {got!r}, expected {exp!r}")
