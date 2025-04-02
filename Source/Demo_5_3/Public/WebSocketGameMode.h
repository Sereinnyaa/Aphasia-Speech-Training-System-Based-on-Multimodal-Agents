#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "WebSocketGameMode.generated.h"

UCLASS()
class DEMO_5_3_API AWebSocketGameMode : public AGameModeBase
{
    GENERATED_BODY()

public:
    virtual void BeginPlay() override;

protected:
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "UI")
    TSubclassOf<class UUserWidget> ChatInterfaceClass;

    UPROPERTY()
    class UUserWidget* ChatInterface;

    UPROPERTY()
    class AWebSocketClient* WebSocketClient;
}; 