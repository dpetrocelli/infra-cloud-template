# Clase 7 — IA: Vertex AI/Ollama/vast.ai · Blockchain: Layer 2 (Base Sepolia)

## Ejemplo IA

- `model/train.py`: entrena un clasificador chiquito (iris, scikit-learn)
  **al construir la imagen**, no en cada arranque del contenedor.
- `model/serve.py`: `POST /predict`, `GET /metrics`, `GET /healthz`. El
  mismo contrato de siempre, para que Helm/Terraform no cambien.

Este servicio es el stand-in local de lo que en la nube sería un endpoint de
Vertex AI, un Ollama autogestionado en una VM con GPU, o una instancia
alquilada en vast.ai: la app que *habla* con el modelo no necesita saber
cuál de los tres hay detrás, mientras el contrato (`/predict`, `/metrics`)
se mantenga.

```bash
docker build -t model:local model/
docker run -d -p 8081:8081 model:local
curl -X POST localhost:8081/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}'
```

## Ejemplo Blockchain

- `contracts/src/Counter.sol` + `contracts/script/Deploy.s.sol`: el mismo
  contrato, compilado una vez, desplegado a Sepolia y a Base Sepolia
  (rollup L2) para comparar gas y latencia en los exploradores de cada red.
- `.github/workflows/contracts.yml`: el job `deploy-testnet` hace exactamente
  eso, disparado por un tag.

```bash
cd contracts
forge test -vv
# Deploy manual (necesita RPC_URL y una clave de testnet, nunca mainnet):
# forge script script/Deploy.s.sol --rpc-url $RPC_URL --private-key $KEY --broadcast
```

Un rollup optimistic asume que las transacciones son válidas y sólo las
disputa si alguien presenta una prueba de fraude (ventana de desafío); un
rollup ZK prueba matemáticamente cada lote antes de aceptarlo. Compará ambos
enfoques en [L2Beat](https://l2beat.com).
