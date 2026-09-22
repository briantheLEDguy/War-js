#pragma once
#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "WarQuestHud.generated.h"

/** Local quest indicators are projected from authored NPC positions, never replicated to other owners. */
UCLASS()
class AEGISWAR_API AWarQuestHud : public AHUD
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
private:
    UPROPERTY(Transient) TObjectPtr<class UTexture2D> VitalsArtwork;
    UPROPERTY(Transient) TObjectPtr<class UTexture2D> MinimapArtwork;
    bool bArtworkLoaded = false;
};
