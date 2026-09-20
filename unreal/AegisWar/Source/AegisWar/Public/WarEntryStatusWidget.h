#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarEntryStatusWidget.generated.h"

class UTextBlock;

UCLASS()
class AEGISWAR_API UWarEntryStatusWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetEntryError(const FText& Error);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
private:
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Message;
    UPROPERTY(Transient) FText EntryError;
};
