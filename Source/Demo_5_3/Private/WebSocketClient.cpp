#include "WebSocketClient.h"
#include "WebSocketsModule.h"
#include "IWebSocket.h"
#include "JsonObjectConverter.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

AWebSocketClient::AWebSocketClient()
{
    PrimaryActorTick.bCanEverTick = true;
    WebSocket = nullptr;
    ServerURL = TEXT("ws://localhost:8765");
}

void AWebSocketClient::BeginPlay()
{
    Super::BeginPlay();
    
    if (!FModuleManager::Get().IsModuleLoaded("WebSockets"))
    {
        FModuleManager::Get().LoadModule("WebSockets");
    }
    
    ConnectToServer();
    
    GetWorld()->GetTimerManager().SetTimer(
        HeartbeatTimerHandle,
        this,
        &AWebSocketClient::SendHeartbeat,
        30.0f,
        true
    );
}

void AWebSocketClient::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if (HeartbeatTimerHandle.IsValid())
    {
        GetWorld()->GetTimerManager().ClearTimer(HeartbeatTimerHandle);
    }
    
    DisconnectFromServer();
    
    Super::EndPlay(EndPlayReason);
}

void AWebSocketClient::ConnectToServer()
{
    if (WebSocket.IsValid())
    {
        return;
    }
    
    WebSocket = FWebSocketsModule::Get().CreateWebSocket(ServerURL);
    
    WebSocket->OnConnected().AddUObject(this, &AWebSocketClient::HandleConnected);
    WebSocket->OnConnectionError().AddUObject(this, &AWebSocketClient::HandleConnectionError);
    WebSocket->OnClosed().AddUObject(this, &AWebSocketClient::HandleClosed);
    WebSocket->OnMessage().AddUObject(this, &AWebSocketClient::HandleMessage);
    
    WebSocket->Connect();
}

void AWebSocketClient::DisconnectFromServer()
{
    if (WebSocket.IsValid())
    {
        WebSocket->Close();
        WebSocket = nullptr;
    }
}

void AWebSocketClient::SendMessage(const FString& Message)
{
    if (WebSocket.IsValid() && WebSocket->IsConnected())
    {
        WebSocket->Send(Message);
    }
}

void AWebSocketClient::HandleMessage(const FString& Message)
{
    TSharedPtr<FJsonObject> JsonObject;
    TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Message);
    
    if (FJsonSerializer::Deserialize(Reader, JsonObject) && JsonObject.IsValid())
    {
        FString MessageType = JsonObject->GetStringField(TEXT("type"));
        
        if (MessageType == TEXT("user_input"))
        {
            FString Content = JsonObject->GetStringField(TEXT("content"));
            OnMessageReceived.Broadcast(FString::Printf(TEXT("用户: %s"), *Content));
        }
        else if (MessageType == TEXT("ai_response"))
        {
            FString Content = JsonObject->GetStringField(TEXT("content"));
            OnMessageReceived.Broadcast(FString::Printf(TEXT("AI: %s"), *Content));
        }
        else if (MessageType == TEXT("assessment_result"))
        {
            TSharedPtr<FJsonObject> Scores = JsonObject->GetObjectField(TEXT("scores"));
            FString Feedback = JsonObject->GetStringField(TEXT("feedback"));
            
            FString ResultString = FString::Printf(
                TEXT("总分: %.2f\n流畅度: %.2f\n完整度: %.2f\n发音分: %.2f\n声调分: %.2f\n\n改进建议:\n%s"),
                Scores->GetNumberField(TEXT("total_score")),
                Scores->GetNumberField(TEXT("fluency_score")),
                Scores->GetNumberField(TEXT("integrity_score")),
                Scores->GetNumberField(TEXT("phone_score")),
                Scores->GetNumberField(TEXT("tone_score")),
                *Feedback
            );
            
            OnAssessmentResultReceived.Broadcast(ResultString);
        }
    }
}

void AWebSocketClient::HandleConnected()
{
    UE_LOG(LogTemp, Log, TEXT("WebSocket连接成功"));
}

void AWebSocketClient::HandleConnectionError(const FString& Error)
{
    UE_LOG(LogTemp, Error, TEXT("WebSocket连接错误: %s"), *Error);
}

void AWebSocketClient::HandleClosed(int32 StatusCode, const FString& Reason, bool bWasClean)
{
    UE_LOG(LogTemp, Log, TEXT("WebSocket连接已关闭 (状态码: %d, 原因: %s, 是否正常关闭: %s)"), 
        StatusCode, *Reason, bWasClean ? TEXT("是") : TEXT("否"));
    
    FTimerHandle ReconnectTimerHandle;
    GetWorld()->GetTimerManager().SetTimer(
        ReconnectTimerHandle,
        this,
        &AWebSocketClient::ConnectToServer,
        5.0f,
        false
    );
}

void AWebSocketClient::SendHeartbeat()
{
    if (WebSocket.IsValid() && WebSocket->IsConnected())
    {
        TSharedPtr<FJsonObject> JsonObject = MakeShared<FJsonObject>();
        JsonObject->SetStringField(TEXT("type"), TEXT("ping"));
        
        FString JsonString;
        TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&JsonString);
        FJsonSerializer::Serialize(JsonObject.ToSharedRef(), Writer);
        
        SendMessage(JsonString);
    }
} 