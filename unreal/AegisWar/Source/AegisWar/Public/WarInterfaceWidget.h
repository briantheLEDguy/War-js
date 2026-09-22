#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarInterfaceWidget.generated.h"

class SVerticalBox;

/** Local navigation only; inventory, quests and GM actions retain their server validation. */
UCLASS()
class AEGISWAR_API UWarInterfaceWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void ShowPage(FName Page);
    FName GetPage() const { return CurrentPage; }
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual FReply NativeOnPreviewMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event) override;
private:
    void Refresh();
    void AddText(const FString& Text, int32 Size = 16);
    void AddButton(const FString& Text, TFunction<void()> Action);
    FName PendingBinding;
    int32 EditingBarId = 0;
    int32 EditingActionSlot = 0;
    FString BindingMessage;
    FName CurrentPage = TEXT("Menu");
    TSharedPtr<SVerticalBox> Body;
};
