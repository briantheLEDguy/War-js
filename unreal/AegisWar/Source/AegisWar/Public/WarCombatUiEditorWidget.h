#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarCombatUiEditorWidget.generated.h"

class SWarCombatUiEditor;
UCLASS()
class AEGISWAR_API UWarCombatUiEditorWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& Geometry,const FKeyEvent& Event) override;
private:
    TSharedPtr<SWarCombatUiEditor> Editor;
};
