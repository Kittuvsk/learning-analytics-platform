
from dataclasses import dataclass
from pathlib import Path
import random

import numpy as np
from faker import Faker


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Dataset directories
DATA_DIR = PROJECT_ROOT / "data"
GENERATED_DIR = DATA_DIR / "generated"
GROUND_TRUTH_DIR = DATA_DIR / "ground_truth"
MANIFEST_DIR = DATA_DIR / "manifests"
PROCESSED_DIR = DATA_DIR / "processed"


# Fixed seed for reproducibility
RANDOM_SEED = 20261022


@dataclass(frozen=True)
class GenerationConfig:

    seed: int = RANDOM_SEED

    # Required dataset sizes
    learner_count: int = 20_000
    course_count: int = 500
    enrollment_count: int = 100_000
    activity_event_count: int = 2_000_000

    # Initial synthetic master-data settings
    cohort_count: int = 100
    content_items_per_course: int = 8


def create_generators(seed: int = RANDOM_SEED):

    python_rng = random.Random(seed)

    numpy_rng = np.random.default_rng(seed)

    fake = Faker("en_US")
    fake.seed_instance(seed)

    return python_rng, numpy_rng, fake


def create_data_directories():

    directories = [
        GENERATED_DIR,
        GROUND_TRUTH_DIR,
        MANIFEST_DIR,
        PROCESSED_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":

    config = GenerationConfig()

    create_data_directories()

    python_rng, numpy_rng, fake = create_generators()

    print("Generator configuration loaded successfully!")

    print(f"Random seed: {config.seed}")
    print(f"Learners: {config.learner_count}")
    print(f"Courses: {config.course_count}")
    print(f"Enrollments: {config.enrollment_count}")
    print(f"Activity events: {config.activity_event_count}")
    print(f"Cohorts: {config.cohort_count}")

    print(f"Project directory: {PROJECT_ROOT}")
    print(f"Generated data directory: {GENERATED_DIR}")

    print("Faker sample:", fake.first_name())
    print("NumPy generator:", numpy_rng.integers(1, 100))
    print("Python random generator:", python_rng.randint(1, 100))
