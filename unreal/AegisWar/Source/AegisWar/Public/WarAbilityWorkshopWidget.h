#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarAbilityWorkshopWidget.generated.h"

class SWarAbilityWorkshop;
UCLASS()
class AEGISWAR_API UWarAbilityWorkshopWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    bool VerifyInteractions(FString& Error);
    bool VerifyAnalysis(FString& Error);
    bool VerifyReview(FString& Error);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
private:
    TSharedPtr<SWarAbilityWorkshop> Workshop;
};
