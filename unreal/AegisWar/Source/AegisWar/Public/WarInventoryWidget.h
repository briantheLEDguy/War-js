#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarInventoryWidget.generated.h"

class SVerticalBox;
class AWarPlayerState;
class AWarCraftingStation;

/** Native owner inventory view; selections carry the revision displayed to the user. */
UCLASS()
class AEGISWAR_API UWarInventoryWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SetCraftingStation(AWarCraftingStation* Station);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
private:
    void Refresh(AWarPlayerState* State);
    TSharedPtr<SVerticalBox> Rows;
    TWeakObjectPtr<AWarPlayerState> DisplayedState;
    int32 DisplayedRevision = INDEX_NONE;
    TWeakObjectPtr<AWarCraftingStation> CraftingStation;
    bool bStationSelected = false;
    FString Search;
    bool bSortByName = false;
};
