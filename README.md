# superset warmer

Superset Warmer is a small proof-of-concept script designed to pre-warm caches and dashboards in Apache Superset, helping improve performance for end users.

## Features

- Pre-warm Superset dashboards and charts
- Configurable targets and schedules
- Dockerized for easy deployment

## Prerequisites

- Docker installed
- Access to a running Superset instance

## Build

```sh
docker build -t superset-warmer .
```

## Run

```sh
docker run -it --name superset-warmer-dev -v $(pwd):/app superset-warmer
```

## Configuration

Create a `config.yaml` file in the project root:

```yaml
url: "http://localhost:8088"  # superset URL
username: "your_username"  # superset username
password: "your_password"  # superset password
```

## Usage

1. Update `config.yaml` with your Superset credentials and dashboard IDs.
2. Start the container as shown above.
3. The warmer will authenticate and trigger cache refreshes for the specified dashboards.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

MIT