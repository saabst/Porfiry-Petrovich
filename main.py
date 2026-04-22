import asyncio
import json
import websockets
import traceback
from config import Config, logger
from docs_manager import GoogleDocsManager
from state_manager import StateManager
from compiler import Compiler

Config.validate()
docs = GoogleDocsManager()
state = StateManager()
compiler = Compiler(docs, state)

async def mcp_handler():
    uri = f"wss://api.xiaozhi.me/mcp/?token={Config.XIAOZHI_TOKEN}"
    while True:
        try:
            async with websockets.connect(uri) as ws:
                logger.info("Порфирий Петрович запущен. Ожидание сообщений...")
                async for message in ws:
                    data = json.loads(message)
                    method = data.get("method")
                    msg_id = data.get("id")

                    if method == "initialize":
                        await ws.send(json.dumps({
                            "jsonrpc": "2.0", "id": msg_id,
                            "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "porfiry", "version": "5.0"}}
                        }))
                        await ws.send(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}))

                    elif method == "tools/list":
                        await ws.send(json.dumps({
                            "jsonrpc": "2.0", "id": msg_id,
                            "result": {"tools": [{
                                "name": "log_diary",
                                "description": "Записать заметку",
                                "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}, "themes": {"type": "array", "items": {"type": "string"}}}, "required": ["text"]}
                            }]}
                        }))

                    elif method == "tools/call":
                        tool_name = data.get("params", {}).get("name")
                        args = data.get("params", {}).get("arguments", {})
                        if tool_name == "log_diary":
                            text = args.get("text", "").strip()
                            themes = args.get("themes", [])
                            st = state.load_state()
                            entry_id = f"L{st['chapter_count']:03d}-{st['entries_count']+1:03d}"
                            docs.append_diary(text, entry_id)
                            should_compile = state.add_entry(text, themes)
                            if should_compile:
                                logger.info("Порог достигнут, запуск компиляции...")
                                asyncio.create_task(compiler.run())
                            await ws.send(json.dumps({
                                "jsonrpc": "2.0", "id": msg_id,
                                "result": {"content": [{"type": "text", "text": f"Заметка {entry_id} сохранена"}]}
                            }))

                    elif method == "ping":
                        await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {}}))

        except Exception as e:
            logger.error(f"Соединение разорвано: {e}\n{traceback.format_exc()}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(mcp_handler())