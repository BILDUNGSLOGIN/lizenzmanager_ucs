from fastapi import FastAPI

import routers.auth
import routers.licenses

router_modules = [routers.auth, routers.licenses]
app = FastAPI()

for router_module in router_modules:
    app.include_router(router_module.router)
