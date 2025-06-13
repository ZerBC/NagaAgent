# mypy: disable - error - code = "no-untyped-def,misc"
import pathlib
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles

# Define the FastAPI app
app = FastAPI()


def create_frontend_router(build_dir="../frontend/dist"):
    """创建用于服务 React 前端的路由。

    参数：
        build_dir: 相对于本文件的 React 构建目录路径。

    返回：
        用于服务前端的 Starlette 应用。
    """
    build_path = pathlib.Path(__file__).parent.parent.parent / build_dir

    if not build_path.is_dir() or not (build_path / "index.html").is_file():
        print(
            f"WARN: 未找到前端构建目录或目录不完整：{build_path}。前端服务可能无法正常工作。"
        )
        # 如果构建未完成，返回一个占位路由
        from starlette.routing import Route

        async def dummy_frontend(request):
            return Response(
                "前端未构建。请在 frontend 目录下运行 'npm run build'。",
                media_type="text/plain",
                status_code=503,
            )

        return Route("/{path:path}", endpoint=dummy_frontend)

    return StaticFiles(directory=build_path, html=True)


# 将前端挂载到 /app，避免与 LangGraph API 路由冲突
app.mount(
    "/app",
    create_frontend_router(),
    name="frontend",
)
