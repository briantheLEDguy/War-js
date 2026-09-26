#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateBrush.h"
#include "Styling/SlateTypes.h"
#include "WarFrontendWidget.generated.h"

class SVerticalBox;
class STextBlock;
class UWarCharacterVisualDefinition;
class UWarFrontendPresentation;
class UMaterialInterface;

/** Native entry UI. Development drafts are explicitly session-only, never account credentials. */
UCLASS()
class AEGISWAR_API UWarFrontendWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void ShowError(const FString& Error);
    static bool ValidateCharacterName(const FString& Name, FString& Error);
protected:
    virtual void NativeConstruct() override;
    virtual void NativeTick(const FGeometry& Geometry, float Delta) override;
    virtual void NativeDestruct() override;
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
private:
    friend class UWarFrontendProof;
    void InitializeArtwork();
    const FButtonStyle& EntryButtonStyle(bool bPrimary) const;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInterface>> Artwork;
    FSlateBrush LogoBrush;
    FSlateBrush WindowBrush;
    FButtonStyle PrimaryButton;
    FButtonStyle SecondaryButton;
    FTableRowStyle ChoiceRow;
    FComboBoxStyle ChoiceBox;
    FCheckBoxStyle MotionCheck;
    void RefreshPreview();
    UPROPERTY(Transient) TObjectPtr<UWarFrontendPresentation> Presentation;
    FSlateBrush CityBrushes[2];
    FSlateBrush CharacterBrush;
    bool bHasDraft = false;
    void ShowLogin();
    void ShowDeveloperAccount();
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
