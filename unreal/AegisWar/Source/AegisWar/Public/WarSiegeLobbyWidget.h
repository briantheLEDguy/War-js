#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarSiegeLobbyWidget.generated.h"

UCLASS()
class AEGISWAR_API UWarSiegeLobbyWidget : public UUserWidget
{
    GENERATED_BODY()
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
};
