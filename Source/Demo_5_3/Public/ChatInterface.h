#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/TextBlock.h"
#include "ChatInterface.generated.h"

UENUM(BlueprintType)
enum class EMessageType : uint8
{
    System UMETA(DisplayName = "System"),
    User UMETA(DisplayName = "User"),
    AI UMETA(DisplayName = "AI"),
    Assessment UMETA(DisplayName = "Assessment")
};

UCLASS()
class DEMO_5_3_API UChatInterface : public UUserWidget
{
    GENERATED_BODY()

public:
    virtual void NativeConstruct() override;

protected:
    UPROPERTY(meta = (BindWidget))
    class UScrollBox* MessageScrollBox;

    UPROPERTY()
    class AWebSocketClient* WebSocketClient;

    UFUNCTION()
    void OnMessageReceived(const FString& Message);

    UFUNCTION()
    void OnAssessmentResultReceived(const FString& Result);

private:
    UTextBlock* CreateMessageText(const FString& Message, EMessageType Type);
}; 