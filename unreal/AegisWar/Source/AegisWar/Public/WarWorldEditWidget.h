#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarWorldEditWidget.generated.h"

class SVerticalBox;

UCLASS()
class AEGISWAR_API UWarWorldEditWidget : public UUserWidget
{
    GENERATED_BODY()
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
private:
    void RefreshRows();
    void SelectNearest();
    void EditSelected(FVector Offset, double Yaw = 0, double Scale = 1, bool bToggleHidden = false);
    FName Selected;
    FString Search;
    TSharedPtr<SVerticalBox> Rows;
    int32 DisplayedRevision = INDEX_NONE;
};
