# topic_config.py

"""
Extrem ausführliche Topic-Konfiguration:
Dieses Mapping deckt ein weites Spektrum an Domänen ab, damit kaum ein Artikel
mehr im Catch-All „Allgemein“ verschwindet.
"""

# Hartes Mapping: Topic → Liste von Keywords (Wortstämmen, Phrasen)
TOPIC_MAPPING = {
    "Allgemein": {"keywords": []},

    # KI-Plattformen & Modelle
    "OpenAI & GPT-Modelle": {
        "keywords": [
            "openai", "gpt-4", "gpt-3", "chatgpt", "dall-e", "codex", "whisper", "embeddings"
        ]
    },
    "Anthropic & Claude": {
        "keywords": ["anthropic", "claude", "claude ai", "claude-instant"]
    },
    "Google AI & Bard": {
        "keywords": ["google ai", "bard", "gemini", "palm", "laMDA", "vertex ai"]
    },
    "Meta AI & LLaMA": {
        "keywords": ["meta ai", "llama", "meta-llama", "opt", "fairseq"]
    },
    "Microsoft AI & Azure": {
        "keywords": ["microsoft", "azure ai", "copilot", "bing chat", "semantic kernel"]
    },
    "Amazon AWS AI": {
        "keywords": ["amazon", "aws ai", "sagemaker", "lex", "polly", "bedrock"]
    },

    # Geräte & Consumer Tech
    "Apple Geräte & Dienste": {
        "keywords": ["apple", "iphone", "ipad", "macos", "ios", "app store", "siri", "vision pro"]
    },
    "Google Produkte": {
        "keywords": ["android", "chrome", "gmail", "maps", "drive", "pixel", "nest"]
    },
    "Meta & Soziale Medien": {
        "keywords": ["facebook", "instagram", "whatsapp", "threads", "tiktok", "snapchat"]
    },
    "Telekommunikation & 5G": {
        "keywords": ["5g", "telekom", "verizon", "vodafone", "bandbreite", "lte"]
    },
    "Halbleiter & Chips": {
        "keywords": ["chip", "prozessor", "gpu", "nvidia", "intel", "tsmc", "arm", "lehmanning"]
    },

    # Infrastruktur & Plattform
    "Cloud Computing & Infrastruktur": {
        "keywords": ["cloud", "saas", "paas", "iaas", "docker", "kubernetes", "openstack"]
    },
    "Edge Computing & IoT": {
        "keywords": ["edge", "iot", "sensor", "embedded", "mqtt", "zigbee"]
    },
    "Container & Kubernetes": {
        "keywords": ["container", "kubernetes", "helm", "docker", "openshift"]
    },
    "DevOps & CI/CD": {
        "keywords": ["ci/cd", "jenkins", "gitlab ci", "github actions", "circleci", "terraform"]
    },
    "Softwareentwicklung & Programmierung": {
        "keywords": [
            "python", "java", "javascript", "typescript", "go", "rust", "c\\+\\+", "flask", "react"
        ]
    },
    "Open Source & Community": {
        "keywords": ["open source", "github", "gitlab", "license", "mit-license"]
    },
    "APIs & Microservices": {
        "keywords": ["api", "rest", "graphql", "microservice", "swagger", "openapi"]
    },

    # Sicherheit & Compliance
    "IT-Sicherheit & Cybersecurity": {
        "keywords": [
            "cybersecurity", "hacker", "malware", "ransomware", "phishing", "firewall", "mfa"
        ]
    },
    "Datenschutz & Compliance": {
        "keywords": ["gdpr", "datenschutz", "compliance", "iso27001", "pdpa", "hipaa"]
    },

    # Blockchain & Finanzen
    "Blockchain & Kryptowährungen": {
        "keywords": [
            "bitcoin", "ethereum", "crypto", "nft", "decentralized", "defi", "smart contract"
        ]
    },
    "FinTech & Banking": {
        "keywords": [
            "fintech", "banking", "payment", "paypal", "stripe", "square", "mobile payment"
        ]
    },
    "Startups & Venture Capital": {
        "keywords": [
            "startup", "seed round", "series a", "venture capital", "pitch", "incubator"
        ]
    },
    "Wirtschaft & Märkte": {
        "keywords": [
            "aktie", "ipo", "börse", "inflation", "wirtschaft", "markttrend", "rezession"
        ]
    },
    "Marketing & Werbung": {
        "keywords": [
            "seo", "sem", "adwords", "marketing", "kampagne", "branding", "influencer"
        ]
    },
    "E-Commerce & Einzelhandel": {
        "keywords": ["e-commerce", "shopify", "woocommerce", "retail", "checkout", "omnichannel"]
    },

    # Vertikale & spezialisierte Domains
    "Biotech & Pharma": {
        "keywords": ["crispr", "impfung", "therapie", "clinical trial", "pharma", "biotech"]
    },
    "Gesundheit & MedTech": {
        "keywords": ["healthtech", "telemedizin", "ehr", "medical device", "wearable"]
    },
    "Bildung & EdTech": {
        "keywords": ["edtech", "online learning", "mooc", "lms", "classroom", "tutor"]
    },
    "Wissenschaft & Forschung": {
        "keywords": [
            "forschung", "studie", "journal", "experiment", "paper", "quantum", "climate science"
        ]
    },
    "Raumfahrt & Satelliten": {
        "keywords": ["space", "rocket", "satellit", "nasa", "spacex", "esa", "starship"]
    },

    # Mobility, Auto & Logistik
    "Automotive & Transport": {
        "keywords": [
            "automotive", "auto", "elektroauto", "tesla", "ford", "volkswagen", "verkehr"
        ]
    },
    "Mobilität & Autonome Systeme": {
        "keywords": [
            "autonom", "self-driving", "robotaxi", "lidar", "mobility", "uber", "waymo"
        ]
    },
    "Logistik & Supply Chain": {
        "keywords": [
            "logistik", "supply chain", "transport", "lager", "shipment", "fleet management"
        ]
    },

    # Medien, Entertainment & Kultur
    "Medien & Entertainment": {
        "keywords": ["film", "serie", "streaming", "review", "trailer", "netflix", "hbo", "disney+"]
    },
    "Streaming & Video": {
        "keywords": ["youtube", "twitch", "vimeo", "live streaming", "webinar"]
    },
    "Gaming & eSports": {
        "keywords": ["gaming", "esports", "playstation", "xbox", "nintendo", "steam", "fortnite"]
    },
    "Musik & Podcast": {"keywords": ["musik", "podcast", "spotify", "apple music", "soundcloud"]},

    # Design, Kunst & Lifestyle
    "Design & UX/UI": {
        "keywords": ["ux", "ui", "design", "figma", "sketch", "wireframe", "prototyp"]
    },
    "Kunst & Kultur": {
        "keywords": ["kunst", "galerie", "museum", "ausstellung", "theater", "literatur"]
    },
    "Lifestyle & Wellness": {
        "keywords": ["wellness", "yoga", "meditation", "fitness", "lifestyle", "fashion"]
    },
    "Sport & Fitness": {
        "keywords": ["sport", "fitness", "workout", "lauf", "marathon", "soccer", "football"]
    },
    "Essen & Getränke": {"keywords": ["food", "restaurant", "rezepte", "cafe", "drinks", "brewery"]},
    "Reisen & Tourismus": {
        "keywords": ["reisen", "tourismus", "hotel", "airbnb", "flug", "vacation"]
    },

    # Umwelt & Energie
    "Nachhaltigkeit & Umwelt": {
        "keywords": ["nachhaltigkeit", "recycling", "klimawandel", "umwelt", "carbon footprint"]
    },
    "Energie & Cleantech": {
        "keywords": ["solar", "wind", "cleantech", "batterie", "energieversorgung", "grid"]
    },

    # Politik, Recht & Gesellschaft
    "Politik & Gesellschaft": {
        "keywords": ["politik", "regierung", "wahlen", "demokratie", "parlament"]
    },
    "Recht & Regulierung": {
        "keywords": ["gesetz", "verordnung", "compliance", "recht", "urteil", "kodex"]
    },
    "Arbeitswelt & HR": {
        "keywords": [
            "hr", "rekrutierung", "talent", "arbeitsplatz", "remote work", "coworking"
        ]
    },
    "Immobilien & Bau": {
        "keywords": ["immobilien", "bau", "architecture", "real estate", "construction"]
    },
}

TOPIC_SYNONYMS = {
    "Allgemein": [
        "general", "misc", "sonstiges", "verschiedenes", "other", "various"
    ],

    "Künstliche Intelligenz & Maschinelles Lernen": [
        "ai", "nlp", "computer vision", "gan",
        "qwen", "qwen-2.5", "32b", "uncensored", "uncensored qwen",
        "llm", "language model", "large language model",
        "grok", "make money with ai", "earnings", "monetize ai"
    ],

    "OpenAI & GPT-Modelle": [
        "openai", "gpt", "gpt-3", "gpt-4", "chatgpt", "dall-e", "codex", "whisper",
        "davinci", "curie", "ada", "embeddings", "text-davinci"
    ],
    "Anthropic & Claude": [
        "anthropic", "claude", "claude ai", "claude-instant", "anthropic.ai"
    ],
    "Google AI & Bard": [
        "google ai", "bard", "gemini", "palm", "laMDA", "vertex ai", "flan", "paLM"
    ],
    "Meta AI & LLaMA": [
        "meta ai", "llama", "meta-llama", "opt", "fairseq", "facebook ai", "mistral"
    ],
    "Microsoft AI & Azure": [
        "microsoft", "azure ai", "azure", "ms azure", "copilot", "semantic kernel",
        "bing chat", "azure ml"
    ],
    "Amazon AWS AI": [
        "amazon", "aws ai", "aws", "sagemaker", "bedrock", "lex", "polly",
        "rekognition", "comprehend", "translate"
    ],

    "Apple Geräte & Dienste": [
        "apple", "iphone", "ipad", "macos", "ios", "macbook", "airpods",
        "apple watch", "apple tv", "app store", "siri", "vision pro", "facetime",
        "imessage", "apple music"
    ],
    "Google Produkte": [
        "google", "android", "chrome", "gmail", "maps", "drive", "pixel",
        "nest", "chromebook", "youtube", "google home", "assistant"
    ],
    "Meta & Soziale Medien": [
        "facebook", "instagram", "whatsapp", "threads", "tiktok", "snapchat",
        "twitter", "x", "social network", "social media"
    ],
    "Telekommunikation & 5G": [
        "5g", "lte", "telekom", "verizon", "vodafone", "bandbreite", "router",
        "broadband", "fiber", "netzanbieter"
    ],
    "Halbleiter & Chips": [
        "chip", "prozessor", "cpu", "gpu", "nvidia", "intel", "arm",
        "tsmc", "semiconductor", "wafer", "fab", "node", "node shrinks"
    ],

    "Cloud Computing & Infrastruktur": [
        "cloud", "aws", "azure", "gcp", "google cloud", "digitalocean",
        "saas", "paas", "iaas", "openstack", "cloud-native"
    ],
    "Edge Computing & IoT": [
        "edge", "edge computing", "iot", "internet der dinge", "embedded",
        "mqtt", "zigbee", "smart home", "sensor", "raspberry pi"
    ],
    "Container & Kubernetes": [
        "docker", "kubernetes", "k8s", "helm", "container", "openshift",
        "docker-compose", "pod", "cluster"
    ],
    "DevOps & CI/CD": [
        "devops", "ci", "cd", "jenkins", "github actions", "gitlab ci",
        "circleci", "bamboo", "pipeline", "terraform", "ansible", "puppet"
    ],
    "Softwareentwicklung & Programmierung": [
        "softwareentwicklung", "programmierung", "coding", "developer",
        "programming", "python", "java", "javascript", "typescript", "php",
        "c++", "c#", "go", "rust", "flask", "django", "react", "vue", "angular"
    ],
    "Open Source & Community": [
        "open source", "oss", "community", "github", "gitlab", "license",
        "mit license", "apache license", "contributors", "fork", "pull request"
    ],
    "APIs & Microservices": [
        "api", "rest", "graphql", "microservice", "web service", "soap",
        "grpc", "openapi", "swagger", "raml"
    ],

    "IT-Sicherheit & Cybersecurity": [
        "cybersecurity", "sicherheit", "infosec", "hacker", "malware",
        "ransomware", "virenschutz", "firewall", "penetration test",
        "penetration testing", "phishing", "brute force"
    ],
    "Datenschutz & Compliance": [
        "datenschutz", "compliance", "gdpr", "dsgvo", "privacy", "pdpa",
        "hipaa", "iso27001", "datensicherheit", "audit"
    ],

    "Blockchain & Kryptowährungen": [
        "blockchain", "crypto", "krypto", "bitcoin", "ethereum", "defi",
        "nft", "smart contract", "decentralized", "web3", "dlt"
    ],
    "FinTech & Banking": [
        "fintech", "banking", "payment", "mobile payment", "paypal", "stripe",
        "square", "digital wallet", "online banking", "neobank"
    ],
    "Startups & Venture Capital": [
        "startup", "venture capital", "vc", "seed funding", "series a",
        "pitch", "incubator", "accelerator", "angel investor"
    ],
    "Wirtschaft & Märkte": [
        "wirtschaft", "ökonomie", "aktien", "börse", "ipo", "inflation",
        "rezession", "markttrend", "finanzmarkt", "gdp", "bnp"
    ],
    "Marketing & Werbung": [
        "marketing", "werbung", "seo", "sem", "adwords", "influencer",
        "kampagne", "branding", "content marketing", "ppc"
    ],
    "E-Commerce & Einzelhandel": [
        "e-commerce", "onlinehandel", "retail", "shopify", "woocommerce",
        "checkout", "shopping cart", "point of sale"
    ],

    "Biotech & Pharma": [
        "biotech", "pharma", "crispr", "impfung", "vaccination",
        "clinical trial", "medizin", "therapie", "molekularbiologie"
    ],
    "Gesundheit & MedTech": [
        "gesundheit", "healthtech", "telemedizin", "ehr",
        "wearable", "medical device", "medtech", "telehealth"
    ],
    "Bildung & EdTech": [
        "bildung", "edtech", "e-learning", "online learning", "mooc",
        "lms", "classroom", "tutor", "learning management"
    ],
    "Wissenschaft & Forschung": [
        "wissenschaft", "forschung", "research", "studie", "experiment",
        "paper", "journal", "peer review", "quantum", "climate science"
    ],
    "Raumfahrt & Satelliten": [
        "raumfahrt", "space", "rakete", "satellit", "nasa", "spacex",
        "esa", "starship", "orbital"
    ],

    "Automotive & Transport": [
        "automotive", "auto", "fahrzeug", "elektroauto", "tesla", "ford",
        "volkswagen", "verkehr", "transport", "mobility"
    ],
    "Mobilität & Autonome Systeme": [
        "mobilität", "autonom", "self-driving", "autonomous vehicle",
        "robotaxi", "lidar", "uber", "waymo", "drone"
    ],
    "Logistik & Supply Chain": [
        "logistik", "supply chain", "lager", "delivery", "shipment",
        "fleet management", "transportkette"
    ],

    "Medien & Entertainment": [
        "film", "serie", "streaming", "review", "trailer", "netflix",
        "hbo", "disney+", "kino", "movie", "tv show"
    ],
    "Streaming & Video": [
        "streaming", "youtube", "twitch", "vimeo", "livestream", "webinar"
    ],
    "Gaming & eSports": [
        "gaming", "esports", "playstation", "xbox", "nintendo", "steam",
        "fortnite", "dota", "csgo"
    ],
    "Musik & Podcast": [
        "musik", "podcast", "spotify", "apple music", "soundcloud",
        "bandcamp", "podcaster"
    ],

    "Design & UX/UI": [
        "ux", "ui", "benutzeroberfläche", "design", "figma",
        "wireframe", "adobe xd", "prototyp", "interaction design"
    ],
    "Kunst & Kultur": [
        "kunst", "kultur", "galerie", "museum", "ausstellung",
        "theater", "literatur", "performance"
    ],
    "Lifestyle & Wellness": [
        "lifestyle", "wellness", "fitness", "yoga", "meditation",
        "fashion", "health", "self-care"
    ],
    "Sport & Fitness": [
        "sport", "fitness", "workout", "lauf", "marathon", "soccer",
        "football", "training"
    ],
    "Essen & Getränke": [
        "essen", "food", "restaurant", "rezepte", "cafe", "drinks",
        "bar", "craft beer", "cocktail"
    ],
    "Reisen & Tourismus": [
        "reisen", "tourismus", "travel", "vacation", "holiday",
        "hotel", "flug", "flugreise"
    ],

    "Nachhaltigkeit & Umwelt": [
        "nachhaltigkeit", "recycling", "klimawandel", "environment",
        "eco", "carbon footprint", "umwelt", "grüne technologie"
    ],
    "Energie & Cleantech": [
        "energie", "cleantech", "solar", "wind", "batterie",
        "grid", "stromversorgung", "renewable energy"
    ],

    "Politik & Gesellschaft": [
        "politik", "gesellschaft", "government", "election",
        "demokratie", "parlament", "policy"
    ],
    "Recht & Regulierung": [
        "recht", "regulierung", "law", "compliance", "urteil",
        "gesetz", "verordnung", "court", "legal"
    ],
    "Arbeitswelt & HR": [
        "hr", "arbeitswelt", "rekrutierung", "talent", "karriere",
        "resume", "personalwesen", "remote work"
    ],
    "Immobilien & Bau": [
        "immobilien", "bau", "real estate", "architecture",
        "construction", "wohnungsmarkt"
    ],
}
