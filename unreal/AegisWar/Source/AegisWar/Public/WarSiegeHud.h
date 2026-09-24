#pragma once
#include "CoreMinimal.h"
#include "WarQuestHud.h"
#include "WarSiegeHud.generated.h"
UCLASS()
class AEGISWAR_API AWarSiegeHud : public AWarQuestHud
{
    GENERATED_BODY()
public:
    virtual void DrawHUD() override;
};
