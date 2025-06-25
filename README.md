# Lambda & Kappa Architecture for Data Processing

This repository contains the full implementation of my Bachelor's thesis project:

**“Comparative analysis and implementation of Lambda and Kappa architectures for data processing: challenges, performance and uses.”**

This project is the implementation part of a thesis that compares Lambda and Kappa architectures in terms of:

- Design complexity

- Performance (latency, throughput)

- Fault tolerance

- Maintainability

If you're interested in the full written thesis (in Macedonian), feel free to reach out.

---

## 📌 Project Overview

This project demonstrates both the **Lambda Architecture** and the **Kappa Architecture** for data processing using modern distributed systems.

- **Lambda** combines **batch** (Spark) and **speed** (Flink) layers.
- **Kappa** uses a single Flink pipeline with real-time + reprocessing logic.

Data is ingested via **Apache Kafka**, persisted in **PostgreSQL**, and monitored with **Prometheus & Grafana**.

![Dockerized Lambda and Kappa Architecture Implementation Diagram](/Implementation_Diagram_Lambda_Kappa_Architectures.jpg)
*Diagram: Dockerized deployment of Lambda and Kappa architectures. Components are isolated via Docker Compose profiles with shared PostgreSQL and monitoring stack. Green = Lambda, Blue = Kappa, Black = Shared.*

---

## 🧱 Technologies Used

- **Apache Kafka** – Event ingestion & message brokering
- **Apache Flink** – Real-time processing & reprocessing (Kappa)
- **Apache Spark** – Batch processing (Lambda)
- **PostgreSQL** – Persistent relational storage
- **Prometheus & Grafana** – System monitoring and dashboarding
- **Docker Compose** – Containerized orchestration
- **Python** – PyFlink / Spark scripts, Kafka producers
- **SQL** – Schema definitions & upsert logic

---

## 📁 Folder Structure
.
├── custom-flink-libs/ # JARs required for Flink (JDBC, Kafka, JSON, Prometheus)

├── helper-scripts/ # Kafka producers, test scripts, data cleaners

├── kafka-data/ # Data & configurations related to Kafka

├── monitoring/ # Prometheus and Grafana dashboards

├── postgres-data/ # Volume directory for PostgreSQL

├── docker-compose.yml # Main stack definition (all services)

├── dockerfile.flink # Dockerfile for custom Flink image

├── *.py # PyFlink & Spark processing scripts

├── *.sql # SQL scripts to create database schemas


---

## 📚 Dataset
From Kaggle Bank Customer Segmentation (1M+ Transactions): https://www.kaggle.com/datasets/shivamb/bank-customer-segmentation/code
- bank_transactions.csv: Simulated financial transactions for testing both architectures.
- Includes account balances, transaction amounts, and metadata for profiling and anomaly detection.

---

## 🧪 Key Features
- Demonstrates the separation of batch and stream layers in Lambda
- Shows how Kappa architecture enables reprocessing via Flink
- Event-time handling using watermarks and tumbling windows
- Efficient anomaly detection logic
- PostgreSQL used for stateful persistence and conflict resolution
- Custom dashboards for visualizing throughput, latency, and anomalies

## 🛠 Skills & Concepts
- Stream & batch processing
- Distributed data architecture
- Data pipeline orchestration
- Event-time windowing & watermarks
- Kafka consumer/producer development
- Flink job authoring (PyFlink)
- Spark session and job management
- Docker-based multi-service deployment
- Metrics scraping and visualization with Prometheus and Grafana

---

## 💡 Future Work
- **Advanced Anomaly Detection**: Implement more sophisticated machine learning models (e.g. SparkMLLib, Flink ML, TensorFlow, PyTorch) for anomaly detection, potentially leveraging historical profiles.

- **Unified Serving Layer**: Develop a serving layer (e.g., using a REST API, or a NoSQL database like Cassandra) to combine results from both Lambda Speed and Batch layers, or the Kappa layer, for client applications.

- **High Load Performance Benchmarking** : Conduct thorough performance evaluations under varying data loads.

- **Dynamic Configuration**: Implement dynamic configuration for Kafka topics, database connections, and anomaly rules.

- **Cloud Deployment**: Explore deployment on cloud infrastructure (e.g., AWS, GCP, Azure) using managed Flink services or Kubernetes.

- **Other Use Cases & Data**: Adapt the architectural patterns to other domains like IoT sensor data, log analysis, or clickstream analytics.

- **Integration with IoT**: Specifically, extend the ingestion layer to integrate directly with IoT platforms (e.g., MQTT brokers, AWS IoT Core) for processing sensor data streams.

---

## ⚠️ Disclaimer

This project represents a **first-version prototype** developed as part of an academic Bachelor's thesis. While the core functionality of both **Lambda** and **Kappa** architectures is implemented and tested, the system is still a **work in progress**.

Some important notes:

- 🛠 The codebase is **not production-hardened** and may contain technical debt, experimental logic, or temporary solutions.
- 🚧 Certain aspects (e.g., configuration flexibility, error handling, job resiliency) are **not fully optimized or modularized**.
- 🔄 Future improvements may include performance benchmarking, enhanced observability, modular container reuse, CI/CD integration, and proper packaging.
- 📌 This repository is maintained for learning, demonstration, and educational purposes.

**Contributions, feedback, and suggestions are welcome!**

> Please use this code responsibly and adapt it at your own discretion if extending or deploying in other environments.

---

## 📜 License 
This project is open-source and available under the [MIT License](LICENSE.md).

---

## 👤 Author
**Georgi Kamchevski**
- LinkedIn: https://www.linkedin.com/in/georgi-kamchevski-85657a1b2/
- Email: g.kamchevski@hotmail.com
