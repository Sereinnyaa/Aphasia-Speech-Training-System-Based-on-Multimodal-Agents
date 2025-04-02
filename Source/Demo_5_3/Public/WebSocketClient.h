#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WebSocketsModule.h"
#include "IWebSocket.h"
#include "WebSocketClient.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnMessageReceived, const FString&, Message);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnAssessmentResultReceived, const FString&, Result);

UCLASS()
class DEMO_5_3_API AWebSocketClient : public AActor
{
    GENERATED_BODY()

public:
    AWebSocketClient();

    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

    // 连接WebSocket服务器
    UFUNCTION(BlueprintCallable, Category = "WebSocket")
    void ConnectToServer();

    // 断开连接
    UFUNCTION(BlueprintCallable, Category = "WebSocket")
    void DisconnectFromServer();

    // 发送消息到服务器
    UFUNCTION(BlueprintCallable, Category = "WebSocket")
    void SendMessage(const FString& Message);

    // 消息接收事件
    UPROPERTY(BlueprintAssignable, Category = "WebSocket")
    FOnMessageReceived OnMessageReceived;

    // 评测结果接收事件
    UPROPERTY(BlueprintAssignable, Category = "WebSocket")
    FOnAssessmentResultReceived OnAssessmentResultReceived;

private:
    // WebSocket连接
    TSharedPtr<IWebSocket> WebSocket;

    // 服务器地址
    FString ServerURL;

    // 处理接收到的消息
    void HandleMessage(const FString& Message);

    // 处理连接状态变化
    void HandleConnected();
    void HandleConnectionError(const FString& Error);
    void HandleClosed(int32 StatusCode, const FString& Reason, bool bWasClean);

    // 心跳检测定时器
    FTimerHandle HeartbeatTimerHandle;
    void SendHeartbeat();
};