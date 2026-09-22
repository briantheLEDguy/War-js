#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarGraphicsWidget.generated.h"

class UWarGraphicsSettings;
class SVerticalBox;

/** Shared overlay preserves the underlying entry form or in-game Options page. */
UCLASS()
class AEGISWAR_API UWarGraphicsWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    static void Open(APlayerController* Controller, UUserWidget* ReturnTo, bool bEntry);
    void Close();
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaTime) override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual void ReleaseSlateResources(bool bChildren) override;
private:
    void Refresh();
    UPROPERTY() TObjectPtr<UWarGraphicsSettings> Settings;
    UPROPERTY() TObjectPtr<UUserWidget> ReturnWidget;
    bool bReturnToEntry = false;
    bool bWasPreviewing = false;
    double NextRefresh = 0;
    FString DisplayKey;
    TSharedPtr<SVerticalBox> Controls;
    TWeakPtr<SWidget> PreviousFocus;
};
