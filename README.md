# Cognito Client

A client to smooth over process of common authentication scenarios
using AWS Cognito. Intended to be used within an interactive terminal 
environment (e.g. Python Notebook, CLI).

## Usage

### Install

```
pip install cognito_client
```

### Use

Create an `.env` file in the format of `examples/env.example` and create a client in the same directory:

```python
client = CognitoClient()
```

OR pass the Cognito identifiers as arguments to the function:

```python
client = CognitoClient(
    client_id="XXX",
    user_pool_id="us-west-XXX",
    identity_pool_id="us-west-2:XXX",
)
```

See `examples/temporary-credentials-example.ipynb`.
