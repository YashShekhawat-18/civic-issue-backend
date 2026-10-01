DEPARTMENTS = [
    {"name": "Road", "code": "ROAD", "description": "Road surfaces, potholes and road repair"},
    {"name": "Sanitation", "code": "SANITATION", "description": "Garbage collection and public toilets"},
    {"name": "Electrical", "code": "ELECTRICAL", "description": "Streetlights and public electrical fittings"},
    {"name": "Water Supply", "code": "WATER_SUPPLY", "description": "Water pipelines and leakage"},
    {"name": "Sewerage", "code": "SEWERAGE", "description": "Sewage lines and overflow"},
    {"name": "Drainage", "code": "DRAINAGE", "description": "Storm water drains and blocked drainage"},
    {"name": "Traffic", "code": "TRAFFIC", "description": "Traffic signals and illegal parking"},
    {"name": "Animal Control", "code": "ANIMAL_CONTROL", "description": "Stray animals"},
    {"name": "Garden", "code": "GARDEN", "description": "Trees, parks and fallen branches"},
    {"name": "Encroachment", "code": "ENCROACHMENT", "description": "Illegal occupation of public land"},
    {"name": "Environment", "code": "ENVIRONMENT", "description": "Noise and pollution complaints"},
    {"name": "General", "code": "GENERAL", "description": "Issues that fit no other department"},
]

CATEGORIES = [
    {"name": "Pothole", "code": "POTHOLE", "departmentCode": "ROAD",
     "description": "Holes or craters in the road surface"},
    {"name": "Garbage", "code": "GARBAGE", "departmentCode": "SANITATION",
     "description": "Uncollected or overflowing garbage"},
    {"name": "Streetlight", "code": "STREETLIGHT", "departmentCode": "ELECTRICAL",
     "description": "Broken or non-working streetlights"},
    {"name": "Water Leakage", "code": "WATER_LEAKAGE", "departmentCode": "WATER_SUPPLY",
     "description": "Leaking water pipes or taps"},
    {"name": "Sewage Overflow", "code": "SEWAGE_OVERFLOW", "departmentCode": "SEWERAGE",
     "description": "Overflowing sewage or manholes"},
    {"name": "Drainage", "code": "DRAINAGE", "departmentCode": "DRAINAGE",
     "description": "Blocked or broken drains"},
    {"name": "Traffic Signal", "code": "TRAFFIC_SIGNAL", "departmentCode": "TRAFFIC",
     "description": "Faulty or missing traffic signals"},
    {"name": "Illegal Parking", "code": "ILLEGAL_PARKING", "departmentCode": "TRAFFIC",
     "description": "Vehicles parked where parking is not allowed"},
    {"name": "Road Damage", "code": "ROAD_DAMAGE", "departmentCode": "ROAD",
     "description": "Cracked, sunken or damaged roads and footpaths"},
    {"name": "Public Toilet", "code": "PUBLIC_TOILET", "departmentCode": "SANITATION",
     "description": "Dirty or broken public toilets"},
    {"name": "Stray Animals", "code": "STRAY_ANIMALS", "departmentCode": "ANIMAL_CONTROL",
     "description": "Stray dogs, cattle or other animals on the road"},
    {"name": "Tree/Fallen Branch", "code": "TREE_FALLEN_BRANCH", "departmentCode": "GARDEN",
     "description": "Fallen trees or branches blocking the way"},
    {"name": "Encroachment", "code": "ENCROACHMENT", "departmentCode": "ENCROACHMENT",
     "description": "Illegal occupation of footpaths or public land"},
    {"name": "Noise Complaint", "code": "NOISE_COMPLAINT", "departmentCode": "ENVIRONMENT",
     "description": "Excessive or illegal noise"},
    {"name": "Other Civic Issue", "code": "OTHER", "departmentCode": "GENERAL",
     "description": "Any civic issue not listed above"},
]

# Sample workers: one per department for four departments.
# Their password comes from SEED_WORKER_PASSWORD in .env.
WORKERS = [
    {"name": "Ravi Kumar", "email": "road.worker@example.com", "departmentCode": "ROAD"},
    {"name": "Sunita Sharma", "email": "sanitation.worker@example.com", "departmentCode": "SANITATION"},
    {"name": "Amit Patil", "email": "electrical.worker@example.com", "departmentCode": "ELECTRICAL"},
    {"name": "Neha Joshi", "email": "water.worker@example.com", "departmentCode": "WATER_SUPPLY"},
]

BADGES = [
    {"name": "Newcomer", "description": "Earned your first points", "icon": "star", "pointsRequired": 10},
    {"name": "Active Citizen", "description": "Regularly helping your city", "icon": "medal", "pointsRequired": 50},
    {"name": "Community Helper", "description": "A trusted voice in your community", "icon": "trophy", "pointsRequired": 150},
    {"name": "City Champion", "description": "Top contributor to a better city", "icon": "crown", "pointsRequired": 500},
]