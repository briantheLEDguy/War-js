#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarActionBarWidget.generated.h"

UCLASS()
class AEGISWAR_API UWarActionBarWidget : public UUserWidget
{
    GENERATED_BODY()
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
};
