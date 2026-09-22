#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WarFrontendWidget.generated.h"

class SVerticalBox;
class STextBlock;
class UWarCharacterVisualDefinition;

/** Native entry UI. Development drafts are explicitly session-only, never account credentials. */
UCLASS()
class AEGISWAR_API UWarFrontendWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void ShowError(const FString& Error);
    static bool ValidateCharacterName(const FString& Name, FString& Error);
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
private:
    void ShowLogin();
    void ShowCreation();
    void ShowSelection();
    void AddHeading(const FString& Title, const FString& Subtitle, int32 Step = 0);
    void AddButton(const FString& Label, TFunction<void()> Action, bool bPrimary = true);
    TSharedPtr<SVerticalBox> Panel;
    TSharedPtr<STextBlock> Status;
    FString CharacterName;
    FString Race = TEXT("Empire");
    FString Career = TEXT("Battle Prelate");
    FString Body = TEXT("Male");
};
