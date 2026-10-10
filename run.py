"""Start the microservice: python run.py [--port 9100]"""

import argparse

import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9100)
    args = parser.parse_args()
    print(f"Abra http://{args.host}:{args.port}  (API: /docs). Ctrl+C para detener.")
    uvicorn.run("app.main:app", host=args.host, port=args.port)
