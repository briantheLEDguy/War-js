#pragma once
#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"
#include "WarCombatUiDrawing.h"

class AWarPlayerController;
class SVerticalBox;
class SWarCombatUiPreview;
/** Runtime Slate editor. Test harnesses route actual Slate pointer/key events to this widget. */
class AEGISWAR_API SWarCombatUiEditor : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SWarCombatUiEditor) {} SLATE_ARGUMENT(TWeakObjectPtr<AWarPlayerController>,Controller) SLATE_END_ARGS()
    void Construct(const FArguments& Args);
    virtual bool SupportsKeyboardFocus() const override { return true; }
    void Select(int32 Id);
    void Move(int32 Id,FVector2D Delta,FVector2D View);
    void Save();
    int32 Selected = 0;
    bool Collapsed = false;
    TWeakObjectPtr<AWarPlayerController> PC;
    FWarCombatUiPreview Preview;
private:
    TSharedPtr<SVerticalBox> Properties;
    void Refresh();
    void Change(TFunction<void(FWarCombatUiStyle&)> Edit,bool Commit);
};
