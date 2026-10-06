#include "WarCombatUiEditorWidget.h"
#include "SWarCombatUiEditor.h"
#include "WarPlayerController.h"

TSharedRef<SWidget> UWarCombatUiEditorWidget::RebuildWidget()
{ SetIsFocusable(true); return SAssignNew(Editor,SWarCombatUiEditor).Controller(Cast<AWarPlayerController>(GetOwningPlayer())); }
void UWarCombatUiEditorWidget::ReleaseSlateResources(bool Children) { Super::ReleaseSlateResources(Children); Editor.Reset(); }
FReply UWarCombatUiEditorWidget::NativeOnPreviewKeyDown(const FGeometry& G,const FKeyEvent& E)
{
    if (E.GetKey()==EKeys::Escape) { if (auto* PC=Cast<AWarPlayerController>(GetOwningPlayer())) PC->SetEditingUi(false); return FReply::Handled(); }
    return Super::NativeOnPreviewKeyDown(G,E);
}
