#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "WarGameMode.generated.h"

class AWarCharacter;
class UWarCharacterVisualDefinition;

/** Development entry only until the Steam ticket and campaign coordinator integration is implemented. */
UCLASS()
class AEGISWAR_API AWarGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AWarGameMode();
    virtual void PreLogin(const FString& Options, const FString& Address, const FUniqueNetIdRepl& UniqueId, FString& ErrorMessage) override;
    virtual void HandleStartingNewPlayer_Implementation(APlayerController* NewPlayer) override;
    virtual APawn* SpawnDefaultPawnAtTransform_Implementation(AController* NewPlayer, const FTransform& SpawnTransform) override;
    virtual void RestartPlayerAtPlayerStart(AController* NewPlayer, AActor* StartSpot) override;
    virtual void FailedToRestartPlayer(AController* NewPlayer) override;
    void RespawnAfterDeath(AWarCharacter* Character);
private:
    bool IsDevelopmentSession() const;
    UWarCharacterVisualDefinition* ResolveVisual(AController* Controller, FString& OutError) const;
    void RejectEntry(APlayerController* Controller, const FString& Error) const;
    int32 DevelopmentJoins = 0;
};
