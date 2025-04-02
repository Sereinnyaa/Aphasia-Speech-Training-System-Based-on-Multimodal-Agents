import asyncio
import websockets
import json
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketServer:
    def __init__(self, host='0.0.0.0', port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.server = None
        
    async def register(self, websocket):
        """注册新的客户端连接"""
        self.clients.add(websocket)
        logger.info(f"新客户端连接。当前连接数: {len(self.clients)}")
        
    async def unregister(self, websocket):
        """注销客户端连接"""
        self.clients.remove(websocket)
        logger.info(f"客户端断开连接。当前连接数: {len(self.clients)}")
        
    async def broadcast(self, message):
        """广播消息给所有连接的客户端"""
        if self.clients:
            # 添加时间戳
            message['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 转换为JSON字符串
            message_str = json.dumps(message)
            
            # 广播给所有客户端
            await asyncio.gather(
                *[client.send(message_str) for client in self.clients]
            )
            
    async def handle_message(self, websocket):
        """处理来自客户端的消息"""
        try:
            async for message in websocket:
                try:
                    # 解析JSON消息
                    data = json.loads(message)
                    logger.info(f"收到消息: {data}")
                    
                    # 这里可以添加消息处理逻辑
                    # 例如：根据消息类型执行不同的操作
                    message_type = data.get('type')
                    if message_type == 'ping':
                        await websocket.send(json.dumps({
                            'type': 'pong',
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }))
                        
                except json.JSONDecodeError:
                    logger.error("收到无效的JSON消息")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': '无效的JSON格式'
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("客户端连接关闭")
        finally:
            await self.unregister(websocket)
            
    async def start(self):
        """启动WebSocket服务器"""
        try:
            
            self.server = await websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                compression=None,  # 禁用 permessage-deflate
                max_size=None
            )
            logger.info(f"WebSocket服务器启动在 ws://{self.host}:{self.port}")
        except Exception as e:
            logger.error(f"WebSocket启动失败: {e}")
        
    async def stop(self):
        """停止WebSocket服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket服务器已停止")
            
    async def handle_connection(self, websocket, path):
        """处理新的WebSocket连接"""
        logger.info(f"收到新的连接请求: {websocket.remote_address}")
        await self.register(websocket)
        logger.info(f"[连接建立] 客户端已连接: {websocket.remote_address}")
        try:
            await self.handle_message(websocket)
        except Exception as e:
            logger.error(f"[错误] 处理客户端消息时出错: {e}")
        finally:
            logger.info(f"[连接断开] 客户端断开连接: {websocket.remote_address}")
            await self.unregister(websocket)

# 创建全局WebSocket服务器实例
websocket_server = WebSocketServer()

async def start_server():
    """启动WebSocket服务器的异步函数"""
    await websocket_server.start()
    
def run_server():
    """运行WebSocket服务器的同步函数"""
    asyncio.run(start_server())
    
if __name__ == "__main__":
    run_server() 