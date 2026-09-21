#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarWorldEditWidget.generated.h"

class SVerticalBox;

UCLASS()
class AEGISWAR_API UWarWorldEditWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SelectObject(FName Id) { Selected = Id; }
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
private:
    void RefreshRows();
    void RefreshCatalog();
    void SelectNearest();
    void PlaceTemplate(FName TemplateId);
    void SnapSelected();
    void SetSelectedComponent(int32 Field, double Value);
    void EditSelected(FVector Offset, double Yaw = 0, double Scale = 1, bool bToggleHidden = false);
    FName Selected;
    FString Search;
    FString CatalogSearch;
    TSharedPtr<SVerticalBox> CatalogRows;
    int32 CatalogMatches = 0, CatalogTotal = 0;
    TSharedPtr<SVerticalBox> Rows;
    int32 DisplayedRevision = INDEX_NONE;
    int32 GridIndex = 0, AngleIndex = 0;
    float LastPanelHeight = 0;
    double GridCentimeters() const;
    double AngleDegrees() const;
};
