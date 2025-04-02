#include "ChatInterface.h"
#include "Components/ScrollBox.h"
#include "Components/TextBlock.h"
#include "WebSocketClient.h"
#include "Kismet/GameplayStatics.h"
#include "Styling/SlateTypes.h"

void UChatInterface::NativeConstruct()
{
    Super::NativeConstruct();

    // 查找WebSocket客户端
    TArray<AActor*> FoundActors;
    UGameplayStatics::GetAllActorsOfClass(GetWorld(), AWebSocketClient::StaticClass(), FoundActors);
    
    if (FoundActors.Num() > 0)
    {
        WebSocketClient = Cast<AWebSocketClient>(FoundActors[0]);
        
        if (WebSocketClient)
        {
            // 绑定消息接收事件
            WebSocketClient->OnMessageReceived.AddDynamic(this, &UChatInterface::OnMessageReceived);
            WebSocketClient->OnAssessmentResultReceived.AddDynamic(this, &UChatInterface::OnAssessmentResultReceived);
        }
    }
}

UTextBlock* UChatInterface::CreateMessageText(const FString& Message, EMessageType Type)
{
    UTextBlock* MessageText = NewObject<UTextBlock>(MessageScrollBox);
    
    // 根据消息类型设置不同的样式
    FSlateColor TextColor;
    FString Prefix;
    float FontSize = 16.0f;
    FLinearColor ShadowColor;
    FVector2D ShadowOffset(1.0f, 1.0f);
    
    switch (Type)
    {
        case EMessageType::System:
            TextColor = FSlateColor(FLinearColor(0.7f, 0.7f, 0.7f)); // 灰色
            Prefix = TEXT("[系统] ");
            FontSize = 14.0f;
            ShadowColor = FLinearColor(0.0f, 0.0f, 0.0f, 0.3f);
            break;
        case EMessageType::User:
            TextColor = FSlateColor(FLinearColor(0.0f, 0.7f, 1.0f)); // 蓝色
            Prefix = TEXT("[用户] ");
            FontSize = 16.0f;
            ShadowColor = FLinearColor(0.0f, 0.0f, 0.0f, 0.5f);
            break;
        case EMessageType::AI:
            TextColor = FSlateColor(FLinearColor(0.0f, 1.0f, 0.0f)); // 绿色
            Prefix = TEXT("[AI] ");
            FontSize = 16.0f;
            ShadowColor = FLinearColor(0.0f, 0.0f, 0.0f, 0.5f);
            break;
        case EMessageType::Assessment:
            TextColor = FSlateColor(FLinearColor(1.0f, 0.8f, 0.0f)); // 黄色
            Prefix = TEXT("[评测] ");
            FontSize = 15.0f;
            ShadowColor = FLinearColor(0.0f, 0.0f, 0.0f, 0.4f);
            break;
    }
    
    // 设置文本属性
    MessageText->SetColorAndOpacity(TextColor);
    MessageText->SetText(FText::FromString(Prefix + Message));
    MessageText->SetAutoWrapText(true);
    
    return MessageText;
}

void UChatInterface::OnMessageReceived(const FString& Message)
{
    if (MessageScrollBox)
    {
        // 根据消息内容判断类型
        EMessageType Type = EMessageType::System;
        if (Message.StartsWith(TEXT("用户:")))
        {
            Type = EMessageType::User;
        }
        else if (Message.StartsWith(TEXT("AI:")))
        {
            Type = EMessageType::AI;
        }
        
        // 创建并添加消息文本
        UTextBlock* MessageText = CreateMessageText(Message, Type);
        MessageScrollBox->AddChild(MessageText);
        
        // 滚动到底部
        MessageScrollBox->ScrollToEnd();
    }
}

void UChatInterface::OnAssessmentResultReceived(const FString& Result)
{
    if (MessageScrollBox)
    {
        // 创建并添加评测结果文本
        UTextBlock* MessageText = CreateMessageText(Result, EMessageType::Assessment);
        MessageScrollBox->AddChild(MessageText);
        
        // 滚动到底部
        MessageScrollBox->ScrollToEnd();
    }
} 