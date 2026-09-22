#include "WarActionBarWidget.h"
#include "WarPlayerController.h"
#include "WarInterfaceStyle.h"
#include "WarUiArtwork.h"
#include "Widgets/Layout/SConstraintCanvas.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Brushes/SlateNoResource.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
    FVector2D BarSize(FVector2D View, int32 Buttons)
    {
        return WarAbilityBarLayout::Fit(View,Buttons);
    }
    class SWarBarHandle : public SCompoundWidget
    {
    public:
        SLATE_BEGIN_ARGS(SWarBarHandle) {} SLATE_ARGUMENT(TWeakObjectPtr<AWarPlayerController>, Controller) SLATE_ARGUMENT(int32, BarId) SLATE_ARGUMENT(TWeakPtr<SConstraintCanvas>, Canvas) SLATE_END_ARGS()
        void Construct(const FArguments& Args)
        {
            PC = Args._Controller; Id = Args._BarId; Canvas = Args._Canvas;
            ChildSlot[SNew(SBox).HeightOverride(26)[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
                .BorderBackgroundColor(WarInterfaceStyle::Gold).HAlign(HAlign_Center).Padding(4)
                [SNew(STextBlock).Text(FText::FromString(FString::Printf(TEXT("DRAG BAR %d"), Id + 1)))
                    .ColorAndOpacity(FLinearColor::Black).Font(FCoreStyle::GetDefaultFontStyle("Bold", 10))]]];
        }
        virtual FReply OnMouseButtonDown(const FGeometry&, const FPointerEvent& Event) override
        {
            if (PC.IsValid() && PC->IsEditingUi() && Event.GetEffectingButton() == EKeys::LeftMouseButton)
                return FReply::Handled().CaptureMouse(SharedThis(this));
            return FReply::Unhandled();
        }
        virtual FReply OnMouseMove(const FGeometry&, const FPointerEvent& Event) override
        {
            if (!HasMouseCapture() || !PC.IsValid() || !PC->IsEditingUi() || !Canvas.IsValid()) return FReply::Unhandled();
            for (const auto& Bar : PC->GetActionBars()) if (Bar.Id == Id)
            {
                const FGeometry& Geometry = Canvas.Pin()->GetCachedGeometry();
                const FVector2D View = Geometry.GetLocalSize();
                const FVector2D Space = View - BarSize(View, Bar.Buttons);
                const FVector2D Delta = Geometry.AbsoluteToLocal(Event.GetScreenSpacePosition()) - Geometry.AbsoluteToLocal(Event.GetLastScreenSpacePosition());
                PC->MoveActionBar(Id, Bar.Position + FVector2D(Delta.X / FMath::Max(1., Space.X), Delta.Y / FMath::Max(1., Space.Y)), false);
                break;
            }
            return FReply::Handled();
        }
        virtual FReply OnMouseButtonUp(const FGeometry&, const FPointerEvent& Event) override
        {
            if (HasMouseCapture() && Event.GetEffectingButton() == EKeys::LeftMouseButton)
            { if (PC.IsValid()) PC->SaveActionBars(); return FReply::Handled().ReleaseMouseCapture(); }
            return FReply::Unhandled();
        }
        virtual void OnMouseCaptureLost(const FCaptureLostEvent& Event) override
        { if (PC.IsValid()) PC->SaveActionBars(); SCompoundWidget::OnMouseCaptureLost(Event); }
    private:
        TWeakObjectPtr<AWarPlayerController> PC;
        TWeakPtr<SConstraintCanvas> Canvas;
        int32 Id = 0;
    };
}

TSharedRef<SWidget> UWarActionBarWidget::RebuildWidget()
{
    SetIsFocusable(false);
    auto* PC = Cast<AWarPlayerController>(GetOwningPlayer());
    auto Root = SNew(SConstraintCanvas);
    if (!PC) return Root;
    const TWeakObjectPtr<AWarPlayerController> Weak(PC);
    const TWeakPtr<SConstraintCanvas> WeakRoot(Root);
    static const FButtonStyle ButtonStyle = FButtonStyle().SetNormal(FSlateNoResource()).SetHovered(FSlateNoResource())
        .SetPressed(FSlateNoResource()).SetNormalPadding(FMargin(0)).SetPressedPadding(FMargin(0));
    for (const auto& Bar : PC->GetActionBars())
    {
        auto Column = SNew(SVerticalBox);
        Column->AddSlot().MaxHeight(26).AutoHeight()[SNew(SWarBarHandle).Controller(Weak).BarId(Bar.Id).Canvas(WeakRoot)
            .Visibility_Lambda([Weak] { return Weak.IsValid() && Weak->IsEditingUi() ? EVisibility::Visible : EVisibility::Hidden; })];
        auto Row = SNew(SHorizontalBox);
        for (int32 Button = 0; Button < Bar.Buttons; ++Button)
        {
            const int32 ActionSlot = Bar.Slot(Button);
            Row->AddSlot().FillWidth(1)
                [SNew(SWarAbilityCell).Index(Button).Count(Bar.Buttons)
                [SNew(SButton).ButtonStyle(&ButtonStyle).IsFocusable(false)
                    .ContentPadding(FMargin(static_cast<float>((WarAbilityBarLayout::Pitch-WarAbilityBarLayout::InnerSize)/2+4),4))
                    .OnClicked_Lambda([Weak, ActionSlot] { if (Weak.IsValid()) Weak->ActivateActionSlot(ActionSlot); return FReply::Handled(); })
                    .ToolTipText_Lambda([Weak, ActionSlot] { return FText::FromString(Weak.IsValid() ? Weak->GetActionSlotView(ActionSlot).Detail : FString()); })
                    [SNew(SVerticalBox)
                        + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).ColorAndOpacity(WarInterfaceStyle::Gold).OverflowPolicy(ETextOverflowPolicy::Ellipsis)
                            .Font(FCoreStyle::GetDefaultFontStyle("Bold", 11))
                            .Text_Lambda([Weak, ActionSlot] { const FKey Key = Weak.IsValid() ? Weak->GetControlKey(WarActionBar::Binding(ActionSlot)) : EKeys::Invalid;
                                return Key.IsValid() ? Key.GetDisplayName() : FText::FromString(TEXT("--")); })]
                        + SVerticalBox::Slot().FillHeight(1).VAlign(VAlign_Center)[SNew(STextBlock).AutoWrapText(true).OverflowPolicy(ETextOverflowPolicy::Ellipsis)
                            .Font(FCoreStyle::GetDefaultFontStyle("Bold", 12))
                            .ColorAndOpacity_Lambda([Weak, ActionSlot] { return Weak.IsValid() && Weak->GetActionSlotView(ActionSlot).bAvailable ? WarInterfaceStyle::Text : WarInterfaceStyle::Muted; })
                            .Text_Lambda([Weak, ActionSlot] { return FText::FromString(Weak.IsValid() ? Weak->GetActionLabel(Weak->GetActionSlot(ActionSlot)) : FString()); })]
                        + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).ColorAndOpacity(WarInterfaceStyle::Gold).OverflowPolicy(ETextOverflowPolicy::Ellipsis)
                            .Font(FCoreStyle::GetDefaultFontStyle("Regular", 11))
                            .Text_Lambda([Weak, ActionSlot] {
                                if (!Weak.IsValid()) return FText::GetEmpty();
                                const auto View = Weak->GetActionSlotView(ActionSlot);
                                return FText::FromString(View.Cooldown > 0 ? FString::Printf(TEXT("%.1f s"), View.Cooldown)
                                    : View.Footer);
                            })]]]];
        }
        Column->AddSlot().FillHeight(1).Padding(WarAbilityBarLayout::Padding(Bar.Buttons))[Row];
        Root->AddSlot().Alignment(FVector2D::ZeroVector).Offset_Lambda([Weak, WeakRoot, Id = Bar.Id] {
            if (Weak.IsValid() && WeakRoot.IsValid()) for (const auto& Current : Weak->GetActionBars()) if (Current.Id == Id)
            {
                const FVector2D View = WeakRoot.Pin()->GetCachedGeometry().GetLocalSize();
                const FVector2D Size = BarSize(View, Current.Buttons);
                return FMargin(Current.Position.X * FMath::Max(0., View.X - Size.X), Current.Position.Y * FMath::Max(0., View.Y - Size.Y), Size.X, Size.Y);
            }
            return FMargin(0);
        })[SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
            [SNew(SBox).WidthOverride(WarAbilityBarLayout::Size(Bar.Buttons).X).HeightOverride(WarAbilityBarLayout::Size(Bar.Buttons).Y)[Column]]];
    }
    Root->AddSlot().Anchors(FAnchors(0.5f, 0)).Alignment(FVector2D(0.5, 0)).Offset(FMargin(0, 12, 620, 90))
        [SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Justification(ETextJustify::Center).ColorAndOpacity(WarInterfaceStyle::Gold)
                .Text_Lambda([Weak] { return FText::FromString(Weak.IsValid() ? Weak->GetClassAbilityStatus() : FString()); })]
            + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Justification(ETextJustify::Center).ColorAndOpacity(WarInterfaceStyle::Gold)
                .Text_Lambda([Weak] { return FText::FromString(Weak.IsValid() ? Weak->GetCombatTargetLabel() : FString()); })]
            + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Justification(ETextJustify::Center).AutoWrapText(true)
                .Text_Lambda([Weak] { return FText::FromString(Weak.IsValid() ? Weak->GetActionMessage() : FString()); })]
            + SVerticalBox::Slot().AutoHeight()[SNew(SButton).IsFocusable(false).HAlign(HAlign_Center)
                .Visibility_Lambda([Weak] { return Weak.IsValid() && Weak->IsEditingUi() ? EVisibility::Visible : EVisibility::Collapsed; })
                .OnClicked_Lambda([Weak] { if (Weak.IsValid()) Weak->SetEditingUi(false); return FReply::Handled(); })
                [SNew(STextBlock).Text(FText::FromString(TEXT("DONE - SAVE UI LAYOUT")))]]];
    return Root;
}
