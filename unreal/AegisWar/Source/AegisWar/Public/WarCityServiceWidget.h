#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarCityServiceWidget.generated.h"
class AWarCityNpc;
class SVerticalBox;
UCLASS()
class AEGISWAR_API UWarCityServiceWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetNpc(AWarCityNpc* Value);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
    virtual void ReleaseSlateResources(bool ReleaseChildren) override;
private:
    void Refresh();
    TWeakObjectPtr<AWarCityNpc> Npc;
    TSharedPtr<SVerticalBox> Rows;
    int32 Revision = INDEX_NONE;
};
