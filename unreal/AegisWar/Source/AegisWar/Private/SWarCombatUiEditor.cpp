#include "SWarCombatUiEditor.h"
#include "WarPlayerController.h"
#include "Rendering/DrawElements.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontMeasure.h"
#include "Widgets/Layout/SConstraintCanvas.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SSpinBox.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Colors/SColorBlock.h"

namespace
{
    TSharedRef<STextBlock> Label(const FString& S,int32 Size=12)
    { return SNew(STextBlock).Text(FText::FromString(S)).Font(FCoreStyle::GetDefaultFontStyle("Regular",Size)).ColorAndOpacity(FLinearColor(.9f,.9f,.92f)).AutoWrapText(true); }
    TSharedRef<SButton> Button(const FString& S,TFunction<void()> F)
    { return SNew(SButton).IsFocusable(false).OnClicked_Lambda([F] { F(); return FReply::Handled(); })[Label(S)]; }
}
class SWarCombatUiPreview;
class SWarCombatHandle : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SWarCombatHandle) {} SLATE_ARGUMENT(TWeakPtr<SWarCombatUiEditor>,Editor) SLATE_ARGUMENT(TWeakPtr<SWarCombatUiPreview>,Preview) SLATE_ARGUMENT(int32,Id) SLATE_END_ARGS()
    void Construct(const FArguments& A) { Editor=A._Editor; Preview=A._Preview; Id=A._Id; SetTag(FName(*FString::Printf(TEXT("CombatUi.%d"),Id))); ChildSlot[SNew(SBox)]; }
    virtual FReply OnMouseButtonDown(const FGeometry&,const FPointerEvent& E) override
    { if (E.GetEffectingButton()!=EKeys::LeftMouseButton || !Editor.IsValid()) return FReply::Unhandled(); Editor.Pin()->Select(Id); return FReply::Handled().CaptureMouse(SharedThis(this)); }
    virtual FReply OnMouseMove(const FGeometry&,const FPointerEvent& E) override;
    virtual FReply OnMouseButtonUp(const FGeometry&,const FPointerEvent& E) override
    { if (!HasMouseCapture() || E.GetEffectingButton()!=EKeys::LeftMouseButton) return FReply::Unhandled(); if (Editor.IsValid()) Editor.Pin()->Save(); return FReply::Handled().ReleaseMouseCapture(); }
    virtual void OnMouseCaptureLost(const FCaptureLostEvent& E) override { if (Editor.IsValid()) Editor.Pin()->Save(); SCompoundWidget::OnMouseCaptureLost(E); }
    int32 Id=0;
private:
    TWeakPtr<SWarCombatUiEditor> Editor;
    TWeakPtr<SWarCombatUiPreview> Preview;
};
class SWarCombatUiPreview : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SWarCombatUiPreview) {} SLATE_ARGUMENT(TWeakPtr<SWarCombatUiEditor>,Editor) SLATE_END_ARGS()
    void Construct(const FArguments& A)
    {
        Editor=A._Editor; SetVisibility(EVisibility::SelfHitTestInvisible);
        auto Root=SNew(SConstraintCanvas).Visibility(EVisibility::SelfHitTestInvisible);
        const TWeakPtr<SWarCombatUiPreview> Weak=SharedThis(this);
        for (int32 I=0;I<FWarCombatUiSettings::Count;++I)
            Root->AddSlot().Offset_Lambda([Weak,I] {
                if (Weak.IsValid()) { const auto B=Weak.Pin()->HitBounds(I); if (B.bIsValid) return FMargin(B.Min.X,B.Min.Y,B.GetSize().X,B.GetSize().Y); }
                return FMargin(0,0,0,0);
            }).ZOrder(I>=20?2:0)[SNew(SWarCombatHandle).Editor(Editor).Preview(Weak).Id(I)
                .Visibility_Lambda([Weak,I] {
                    if (!Weak.IsValid() || !Weak.Pin()->Editor.IsValid()) return EVisibility::Collapsed;
                    const auto E=Weak.Pin()->Editor.Pin(); if (!E->PC.IsValid()) return EVisibility::Collapsed;
                    const auto& Settings=E->PC->GetCombatUiSettings(); bool Visible=Settings.Styles[I].Visible;
                    if (I<20 && int32(WarCombatUi::Part(I))>=6) Visible &= Settings.Styles[WarCombatUi::Id(EWarCombatUiPart::Panel,I>=10)].Visible;
                    return (Visible || I==E->Selected) && Weak.Pin()->HitBounds(I).bIsValid?EVisibility::Visible:EVisibility::Collapsed;
                })];
        ChildSlot[Root];
    }
    FBox2D HitBounds(int32 I) const
    {
        const auto P=WarCombatUi::Part(I);
        if (P>=EWarCombatUiPart::Damage && P<=EWarCombatUiPart::Healing && Editor.IsValid() && Editor.Pin()->PC.IsValid()
            && Editor.Pin()->PC->GetCombatUiSettings().Styles[I].Visible)
        {
            // Hit-test the actual glyph area, so overlapping stream regions do not steal clicks.
            FBox2D B(ForceInit);
            for (const auto& Item:Draw.Items) if (Item.Element==I && Item.Kind==EWarUiDraw::Text) { B+=Item.A; B+=Item.A+Item.B; }
            return B;
        }
        const auto* B=Draw.Handles.Find(I); return B?*B:FBox2D(ForceInit);
    }
    virtual void Tick(const FGeometry& G,double Time,float Delta) override
    {
        SCompoundWidget::Tick(G,Time,Delta);
        if (!Editor.IsValid() || !Editor.Pin()->PC.IsValid()) return;
        auto E=Editor.Pin(); E->Preview.Advance(Delta,E->PC->GetCombatUiSettings());
        Draw=E->Preview.Draw(E->PC->GetCombatUiSettings(),G.GetLocalSize(),E->Selected);
    }
    virtual int32 OnPaint(const FPaintArgs& Args,const FGeometry& G,const FSlateRect& Culling,FSlateWindowElementList& Out,int32 Layer,const FWidgetStyle& Style,bool Enabled) const override
    {
        const auto Brush=FCoreStyle::Get().GetBrush("WhiteBrush");
        for (const auto& Item:Draw.Items)
        {
            if (Item.Kind==EWarUiDraw::Box)
                FSlateDrawElement::MakeBox(Out,Layer,G.ToPaintGeometry(Item.B,FSlateLayoutTransform(Item.A)),Brush,ESlateDrawEffect::None,Item.Color);
            else if (Item.Kind==EWarUiDraw::Line)
                FSlateDrawElement::MakeLines(Out,Layer,G.ToPaintGeometry(),{Item.A,Item.B},ESlateDrawEffect::None,Item.Color,true,Item.Weight);
            else
            {
                auto Font=FCoreStyle::GetDefaultFontStyle("Regular",FMath::Max(1,FMath::RoundToInt(Item.Weight)));
                const auto Measure=FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
                const auto Size=Measure->Measure(Item.Text,Font);
                const float Fit=FMath::Min(1.f,static_cast<float>(Item.B.X/FMath::Max(1.,Size.X)));
                Font.Size=FMath::Max(1,FMath::RoundToInt(Font.Size*Fit));
                FSlateDrawElement::MakeText(Out,Layer,G.ToPaintGeometry(Item.B,FSlateLayoutTransform(Item.A)),Item.Text,Font,ESlateDrawEffect::None,Item.Color);
            }
        }
        if (Editor.IsValid()) if (const auto* B=Draw.Handles.Find(Editor.Pin()->Selected))
        {
            const TArray<FVector2D> Points={B->Min,FVector2D(B->Max.X,B->Min.Y),B->Max,FVector2D(B->Min.X,B->Max.Y),B->Min};
            FSlateDrawElement::MakeLines(Out,Layer+1,G.ToPaintGeometry(),Points,ESlateDrawEffect::None,FLinearColor(1,.85f,.25f),true,1);
        }
        return SCompoundWidget::OnPaint(Args,G,Culling,Out,Layer+2,Style,Enabled);
    }
    FWarCombatUiDrawList Draw;
    TWeakPtr<SWarCombatUiEditor> Editor;
};
FReply SWarCombatHandle::OnMouseMove(const FGeometry&,const FPointerEvent& E)
{
    if (!HasMouseCapture() || !Editor.IsValid() || !Preview.IsValid()) return FReply::Unhandled();
    const auto G=Preview.Pin()->GetCachedGeometry();
    Editor.Pin()->Move(Id,G.AbsoluteToLocal(E.GetScreenSpacePosition())-G.AbsoluteToLocal(E.GetLastScreenSpacePosition()),G.GetLocalSize());
    return FReply::Handled();
}
void SWarCombatUiEditor::Construct(const FArguments& A)
{
    PC=A._Controller; SetVisibility(EVisibility::SelfHitTestInvisible); Preview.Replay(1);
    const TWeakPtr<SWarCombatUiEditor> Weak=SharedThis(this);
    auto Elements=SNew(SVerticalBox);
    Elements->AddSlot().AutoHeight()[Label(TEXT("COMBAT UI"),18)];
    Elements->AddSlot().AutoHeight().Padding(0,4)[Label(TEXT("Drag an element or select it below. Blue/red outlines identify the preview sides."))];
    for (int32 I=0;I<FWarCombatUiSettings::Count;++I)
        Elements->AddSlot().AutoHeight().Padding(0,1)[Button(WarCombatUi::Label(I),[Weak,I] { if (Weak.IsValid()) Weak.Pin()->Select(I); })];
    auto Toolbar=SNew(SHorizontalBox);
    for (int32 I=0;I<3;++I) Toolbar->AddSlot().AutoWidth().Padding(2)[Button(I==0?TEXT("Single hit"):I==1?TEXT("20-proc burst"):TEXT("Healing"),[Weak,I] { if (Weak.IsValid()) Weak.Pin()->Preview.Replay(I); })];
    Toolbar->AddSlot().AutoWidth().Padding(2)[SNew(SButton).IsFocusable(false).OnClicked_Lambda([Weak] { if (Weak.IsValid()) Weak.Pin()->Preview.Paused=!Weak.Pin()->Preview.Paused; return FReply::Handled(); })
        [SNew(STextBlock).Text_Lambda([Weak] { return FText::FromString(Weak.IsValid() && Weak.Pin()->Preview.Paused?TEXT("Resume"):TEXT("Pause")); })]];
    Toolbar->AddSlot().AutoWidth().Padding(2)[Button(TEXT("Replay"),[Weak] { if (Weak.IsValid()) Weak.Pin()->Preview.Replay(Weak.Pin()->Preview.Mode); })];
    Toolbar->AddSlot().AutoWidth().Padding(2)[Button(TEXT("Done / save"),[Weak] { if (Weak.IsValid() && Weak.Pin()->PC.IsValid()) Weak.Pin()->PC->SetEditingUi(false); })];
    auto PropertyColumn=SNew(SVerticalBox);
    PropertyColumn->AddSlot().AutoHeight()[Button(TEXT("Properties - expand / collapse"),[Weak] { if (Weak.IsValid()) Weak.Pin()->Collapsed=!Weak.Pin()->Collapsed; })];
    PropertyColumn->AddSlot().FillHeight(1)[SNew(SScrollBox).Visibility_Lambda([Weak] { return Weak.IsValid() && Weak.Pin()->Collapsed?EVisibility::Collapsed:EVisibility::Visible; })
        +SScrollBox::Slot()[SAssignNew(Properties,SVerticalBox)]];
    ChildSlot[SNew(SOverlay)
        +SOverlay::Slot()[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
            .BorderBackgroundColor(FLinearColor(.012f,.02f,.032f,.98f)).Visibility(EVisibility::HitTestInvisible)]
        +SOverlay::Slot().Padding(236,58,276,130)[SNew(SWarCombatUiPreview).Editor(Weak)]
        +SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Top).Padding(0,8)[Toolbar]
        +SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Top).Padding(8,64,0,142)[SNew(SBox).WidthOverride(220).MaxDesiredHeight(490)
            [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.025f,.035f,.055f)).Padding(8)[SNew(SScrollBox)+SScrollBox::Slot()[Elements]]]]
        +SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Top).Padding(0,64,8,142)[SNew(SBox).WidthOverride(260).MaxDesiredHeight(490)
            [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.025f,.035f,.055f)).Padding(8)[PropertyColumn]]]];
    Refresh();
}
void SWarCombatUiEditor::Select(int32 I)
{
    if (I<0 || I>=FWarCombatUiSettings::Count) return;
    // Commit the old field before replacing it, so focus loss cannot write into the new selection.
    FSlateApplication::Get().ClearKeyboardFocus(EFocusCause::Cleared);
    Selected=I; Refresh(); FSlateApplication::Get().SetKeyboardFocus(SharedThis(this),EFocusCause::SetDirectly);
}
void SWarCombatUiEditor::Move(int32 I,FVector2D Delta,FVector2D View)
{ if (PC.IsValid()) PC->MoveCombatUi(I,Delta,View,FMath::Clamp(static_cast<float>(View.Y/900),.8f,1.5f),false); }
void SWarCombatUiEditor::Save() { if (PC.IsValid()) PC->SaveCombatUiSettings(); }
void SWarCombatUiEditor::Change(TFunction<void(FWarCombatUiStyle&)> Edit,bool Commit)
{
    if (!PC.IsValid()) return;
    auto S=PC->GetCombatUiSettings().Styles[Selected]; Edit(S); PC->SetCombatUiStyle(Selected,S,Commit);
    const bool Paused=Preview.Paused; float Remaining=Preview.Time;
    Preview.Replay(Preview.Mode); Preview.Advance(0,PC->GetCombatUiSettings());
    while (Remaining>0) { const float Delta=FMath::Min(Remaining,1.f); Preview.Advance(Delta,PC->GetCombatUiSettings()); Remaining-=Delta; }
    Preview.Paused=Paused;
}
void SWarCombatUiEditor::Refresh()
{
    if (!Properties || !PC.IsValid()) return;
    Properties->ClearChildren(); const TWeakPtr<SWarCombatUiEditor> Weak=SharedThis(this); const int32 I=Selected;
    Properties->AddSlot().AutoHeight().Padding(0,6)[Label(WarCombatUi::Label(I),16)];
    Properties->AddSlot().AutoHeight()[Label(WarCombatUi::ScreenRelative(I)?TEXT("Position: screen fraction (0 to 1)"):int32(WarCombatUi::Part(I))>=6?TEXT("Position: pixels from target panel"):TEXT("Position: pixels from target body/head"))];
    for (bool Shadow:{false,true})
    {
        const auto Part=WarCombatUi::Part(I);
        if (Shadow && !((Part>=EWarCombatUiPart::Damage && Part<=EWarCombatUiPart::Healing) || Part==EWarCombatUiPart::Name || Part==EWarCombatUiPart::HealthText)) continue;
        Properties->AddSlot().AutoHeight()[SNew(SCheckBox)
            .IsChecked_Lambda([Weak,Shadow] { if (!Weak.IsValid() || !Weak.Pin()->PC.IsValid()) return ECheckBoxState::Unchecked; const auto& S=Weak.Pin()->PC->GetCombatUiSettings().Styles[Weak.Pin()->Selected]; return (Shadow?S.Shadow:S.Visible)?ECheckBoxState::Checked:ECheckBoxState::Unchecked; })
            .OnCheckStateChanged_Lambda([Weak,Shadow](ECheckBoxState State) { if (Weak.IsValid()) Weak.Pin()->Change([=](auto& S) { (Shadow?S.Shadow:S.Visible)=State==ECheckBoxState::Checked; },true); })[Label(Shadow?TEXT("Text shadow"):TEXT("Visible"))]];
    }
    for (const auto F:WarCombatUi::Fields(I))
        Properties->AddSlot().AutoHeight().Padding(0,3)[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)[Label(F.Name)]
            +SHorizontalBox::Slot().AutoWidth()[SNew(SBox).WidthOverride(94)[SNew(SSpinBox<float>).Tag(FName(F.Name)).MinValue(F.Min).MaxValue(F.Max).Delta(F.Max<=2?.01f:1.f)
                .Value_Lambda([Weak,F] { return Weak.IsValid() && Weak.Pin()->PC.IsValid()?Weak.Pin()->PC->GetCombatUiSettings().Styles[Weak.Pin()->Selected].*(F.Member):0.f; })
                .OnValueChanged_Lambda([Weak,F](float V) { if (Weak.IsValid()) Weak.Pin()->Change([=](auto& S) { S.*(F.Member)=V; },false); })
                .OnValueCommitted_Lambda([Weak,F](float V,ETextCommit::Type) { if (Weak.IsValid()) Weak.Pin()->Change([=](auto& S) { S.*(F.Member)=V; },true); })
                .OnEndSliderMovement_Lambda([Weak](float) { if (Weak.IsValid()) Weak.Pin()->Save(); })]]];
    for (int32 C=0;C<6;++C)
    {
        const FString Name=WarCombatUi::ColorLabel(I,C); if (Name.IsEmpty()) continue;
        Properties->AddSlot().AutoHeight().Padding(0,8,0,2)[Label(Name)];
        Properties->AddSlot().AutoHeight()[SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth()[SNew(SColorBlock).Size(FVector2D(24,24)).Color_Lambda([Weak,C] { return Weak.IsValid() && Weak.Pin()->PC.IsValid()?Weak.Pin()->PC->GetCombatUiSettings().Styles[Weak.Pin()->Selected].Colors[C]:FLinearColor::White; })]
            +SHorizontalBox::Slot().FillWidth(1)[SNew(SEditableTextBox).Tag(FName(*FString::Printf(TEXT("Color%d"),C))).HintText(FText::FromString(TEXT("RRGGBBAA")))
                .Text_Lambda([Weak,C] { return FText::FromString(Weak.IsValid() && Weak.Pin()->PC.IsValid()?Weak.Pin()->PC->GetCombatUiSettings().Styles[Weak.Pin()->Selected].Colors[C].ToFColorSRGB().ToHex():TEXT("")); })
                .OnTextCommitted_Lambda([Weak,C](const FText& T,ETextCommit::Type) {
                    FString Hex=T.ToString(); Hex.RemoveFromStart(TEXT("#")); if (Hex.Len()!=6 && Hex.Len()!=8) return;
                    for (TCHAR Ch:Hex) if (!FChar::IsHexDigit(Ch)) return;
                    if (Weak.IsValid()) Weak.Pin()->Change([=](auto& S) { S.Colors[C]=FLinearColor::FromSRGBColor(FColor::FromHex(Hex)); },true);
                })]];
        auto RGB=SNew(SHorizontalBox);
        for (int32 Channel=0;Channel<4;++Channel)
            RGB->AddSlot().FillWidth(1).Padding(1)[SNew(SSpinBox<float>).MinValue(0).MaxValue(255).Delta(1).ToolTipText(FText::FromString(Channel==0?TEXT("Red"):Channel==1?TEXT("Green"):Channel==2?TEXT("Blue"):TEXT("Alpha")))
                .Value_Lambda([Weak,C,Channel] { if (!Weak.IsValid() || !Weak.Pin()->PC.IsValid()) return 0.f; const auto Color=Weak.Pin()->PC->GetCombatUiSettings().Styles[Weak.Pin()->Selected].Colors[C].ToFColorSRGB(); return float(Channel==0?Color.R:Channel==1?Color.G:Channel==2?Color.B:Color.A); })
                .OnValueChanged_Lambda([Weak,C,Channel](float V) { if (Weak.IsValid()) Weak.Pin()->Change([=](auto& S) { auto Color=S.Colors[C].ToFColorSRGB(); const uint8 B=FMath::Clamp(FMath::RoundToInt(V),0,255); if (Channel==0) Color.R=B; else if (Channel==1) Color.G=B; else if (Channel==2) Color.B=B; else Color.A=B; S.Colors[C]=FLinearColor::FromSRGBColor(Color); },false); })
                .OnValueCommitted_Lambda([Weak](float,ETextCommit::Type) { if (Weak.IsValid()) Weak.Pin()->Save(); })
                .OnEndSliderMovement_Lambda([Weak](float) { if (Weak.IsValid()) Weak.Pin()->Save(); })];
        Properties->AddSlot().AutoHeight()[RGB];
        auto Swatches=SNew(SHorizontalBox);
        for (const FLinearColor Color:{FLinearColor(1,.08f,.06f),FLinearColor(.08f,.45f,1),FLinearColor(.3f,1,.4f),FLinearColor(1,.7f,.2f),FLinearColor::White})
            Swatches->AddSlot().FillWidth(1)[SNew(SButton).IsFocusable(false).OnClicked_Lambda([Weak,C,Color] { if (Weak.IsValid()) Weak.Pin()->Change([=](auto& S) { S.Colors[C]=Color; },true); return FReply::Handled(); })[SNew(SColorBlock).Size(FVector2D(20,12)).Color(Color)]];
        Properties->AddSlot().AutoHeight()[Swatches];
    }
    Properties->AddSlot().AutoHeight().Padding(0,8)[Button(TEXT("Reset element"),[Weak] { FSlateApplication::Get().ClearKeyboardFocus(EFocusCause::Cleared); if (Weak.IsValid() && Weak.Pin()->PC.IsValid()) { Weak.Pin()->PC->ResetCombatUi(Weak.Pin()->Selected); Weak.Pin()->Select(Weak.Pin()->Selected); } })];
    if (I<20) Properties->AddSlot().AutoHeight()[Button(TEXT("Copy to other side"),[Weak] { FSlateApplication::Get().ClearKeyboardFocus(EFocusCause::Cleared); if (Weak.IsValid() && Weak.Pin()->PC.IsValid()) { Weak.Pin()->PC->CopyCombatUiSide(Weak.Pin()->Selected); Weak.Pin()->Select(Weak.Pin()->Selected); } })];
    Properties->AddSlot().AutoHeight().Padding(0,4)[Button(TEXT("Reset combat UI"),[Weak] { FSlateApplication::Get().ClearKeyboardFocus(EFocusCause::Cleared); if (Weak.IsValid() && Weak.Pin()->PC.IsValid()) { Weak.Pin()->PC->ResetCombatUi(); Weak.Pin()->Select(Weak.Pin()->Selected); } })];
}
