#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "WarCombatReviewGameMode.generated.h"

/** The isolated animation gallery has no gameplay pawn, admission or combat authority. */
UCLASS()
class AEGISWAR_API AWarCombatReviewGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AWarCombatReviewGameMode() { DefaultPawnClass = nullptr; }
};
