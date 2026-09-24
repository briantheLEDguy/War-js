#include "SWarAbilityWorkshop.h"
#include "WarAbilityWorkshopSubsystem.h"
#include "WarAbilityCatalog.h"
#include "WarPlayerController.h"
#include "Engine/GameInstance.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SScrollBar.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SComboButton.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SSearchBox.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Views/STableRow.h"
#include "Framework/Application/SlateApplication.h"
#include "HAL/PlatformApplicationMisc.h"
#include "Misc/ConfigCacheIni.h"

using namespace WarWorkshopJson;
namespace
{
    const FLinearColor Ink(.86f,.9f,.96f),Muted(.48f,.57f,.68f),Accent(.27f,.77f,.78f),Panel(.032f,.046f,.065f),Line(.08f,.11f,.15f);
    FString N(double V) { return FString::SanitizeFloat(V,0); }
    bool NumericFilter(const FString& Value,const FString& Filter)
    {
        if (!Value.IsNumeric()) return false;
        const double V=FCString::Atod(*Value); FString A,B;
        if (Filter.Split(TEXT(".."),&A,&B)) return (A.IsEmpty() || (A.IsNumeric() && V>=FCString::Atod(*A))) && (B.IsEmpty() || (B.IsNumeric() && V<=FCString::Atod(*B)));
        for (const FString Op : {TEXT(">="),TEXT("<="),TEXT(">"),TEXT("<"),TEXT("=")})
            if (Filter.StartsWith(Op)) { const FString Tail=Filter.Mid(Op.Len()); if (!Tail.IsNumeric()) return false; const double R=FCString::Atod(*Tail); return Op==TEXT(">=") ? V>=R : Op==TEXT("<=") ? V<=R : Op==TEXT(">") ? V>R : Op==TEXT("<") ? V<R : V==R; }
        return Filter.IsNumeric() && V==FCString::Atod(*Filter);
    }
    FString ConditionWords(const TSharedPtr<FJsonObject>& Node)
    {
        const FString Kind=Text(Node,TEXT("kind"));
        if (Kind==TEXT("all") || Kind==TEXT("any")) { TArray<FString> Children; for (const auto& V:Array(Node,TEXT("children"))) Children.Add(ConditionWords(V->AsObject())); return TEXT("(")+FString::Join(Children,Kind==TEXT("all") ? TEXT(" AND ") : TEXT(" OR "))+TEXT(")"); }
        bool Not=false; Node->TryGetBoolField(TEXT("not"),Not);
        const TMap<FString,FString> Names{{TEXT("hot"),TEXT("HoT")},{TEXT("dot"),TEXT("DoT")},{TEXT("ability_effect"),TEXT("active ability effect")},{TEXT("effect"),TEXT("specific effect")},{TEXT("casting"),TEXT("casting/channeling")}};
        return Text(Node,TEXT("subject"))+(Not ? TEXT(" IS NOT ") : TEXT(" IS "))+Names.FindRef(Kind)+TEXT(" [")+Text(Node,TEXT("source"))+TEXT("]");
    }
    void CollectChecks(const TSharedPtr<FJsonObject>& Node,const TCHAR* Field,TSet<FString>& Out)
    { if (!Node) return; if (Node->HasField(TEXT("children"))) for (const auto& V:Array(Node,TEXT("children"))) CollectChecks(V->AsObject(),Field,Out); else { const FString V=Text(Node,Field); if (!V.IsEmpty()) Out.Add(V); } }
}

void SWarAbilityWorkshop::Construct(const FArguments&,AWarPlayerController* InOwner)
{
    Owner=InOwner; if (InOwner) Store=InOwner->GetGameInstance()->GetSubsystem<UWarAbilityWorkshopSubsystem>();
    SetPreset(Preset); Build(); Refresh();
}
TSharedRef<SWidget> SWarAbilityWorkshop::Label(const FString& Value,bool bMuted) const
{ return SNew(STextBlock).Text(FText::FromString(Value)).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).ColorAndOpacity(bMuted ? Muted : Ink); }
TSharedRef<SWidget> SWarAbilityWorkshop::Button(const FString& Value,TFunction<void()> Action)
{ return SNew(SButton).ContentPadding(FMargin(10,6)).OnClicked_Lambda([Action] { Action(); return FReply::Handled(); })[Label(Value)]; }
TSharedRef<SWidget> SWarAbilityWorkshop::Choice(const FString& Value,const TArray<TPair<FString,FString>>& Options,TFunction<void(FString)> Action)
{
    FString Name=Value; for (const auto& O:Options) if (O.Key==Value) Name=O.Value;
    auto Selected=MakeShared<FString>(Name); auto Menu=SNew(SVerticalBox);
    for (const auto& Option:Options) Menu->AddSlot().AutoHeight()[Button(Option.Value,[Action,Selected,Option] { *Selected=Option.Value; FSlateApplication::Get().DismissAllMenus(); Action(Option.Key); })];
    return SNew(SComboButton).ButtonContent()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).ColorAndOpacity(Ink).Text_Lambda([Selected] { return FText::FromString(*Selected); })]
        .MenuContent()[SNew(SBox).MaxDesiredHeight(450)[SNew(SScrollBox)+SScrollBox::Slot()[Menu]]];
}
TSharedRef<SWidget> SWarAbilityWorkshop::Field(const FString& Name,const FString& Value,TFunction<void(FString)> Action)
{
    return SNew(SVerticalBox)+SVerticalBox::Slot().AutoHeight().Padding(0,6,0,3)[Label(Name,true)]
        +SVerticalBox::Slot().AutoHeight()[SNew(SEditableTextBox).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).Text(FText::FromString(Value))
            .OnTextCommitted_Lambda([Action](const FText& Text,ETextCommit::Type Type) { if (Type!=ETextCommit::OnCleared) Action(Text.ToString()); })];
}
TSharedRef<SWidget> SWarAbilityWorkshop::NumericField(const FString& Name,double Value,TFunction<void(double)> Action)
{ return Field(Name,N(Value),[this,Action](FString V) { if (!V.IsNumeric() || !FMath::IsFinite(FCString::Atod(*V))) Notice=TEXT("Enter a finite number."); else Action(FCString::Atod(*V)); }); }
void SWarAbilityWorkshop::Build()
{
    SAssignNew(Root,SVerticalBox);
    ChildSlot.Padding(TAttribute<FMargin>::CreateLambda([this] { return bMaximized ? FMargin(12) : FMargin(72,48); }))
        [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(Panel).Padding(16)[Root.ToSharedRef()]];
    auto Title=SNew(SHorizontalBox);
    Title->AddSlot().AutoWidth()[SNew(STextBlock).Text(FText::FromString(TEXT("Ability Workshop"))).Font(FCoreStyle::GetDefaultFontStyle("Bold",18)).ColorAndOpacity(Ink)];
    Title->AddSlot().FillWidth(1).Padding(20,5)[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",10.5)).ColorAndOpacity(Accent).Text_Lambda([this] {
        const auto* Catalog=Owner.IsValid() ? Owner->GetGameInstance()->GetSubsystem<UWarAbilityCatalog>() : nullptr;
        return FText::FromString(Store.IsValid() ? Store->GetEnvironment()+TEXT("  |  Active ")+(Catalog ? Catalog->GetVersion().Left(16) : TEXT("unknown"))+TEXT("  |  Draft r")+N(Number(Store->Document().Get(),TEXT("revision"))) : TEXT("Unavailable")); })];
    Title->AddSlot().AutoWidth()[Button(TEXT("Maximize / restore"),[this] { bMaximized=!bMaximized; })];
    Title->AddSlot().AutoWidth().Padding(8,0)[Button(TEXT("Close"),[this] { if (Store.IsValid()) Store->SaveLocal(); if (Owner.IsValid()) Owner->CloseAllPanels(); })];
    Root->AddSlot().AutoHeight().Padding(0,0,0,12)[Title];
    auto Tabs=SNew(SHorizontalBox);
    for (const FString Page:{TEXT("Class Abilities"),TEXT("Ability Library"),TEXT("Test Arena"),TEXT("Version History")})
        Tabs->AddSlot().AutoWidth().Padding(0,0,8,0)[Button(Page,[this,Page] { Tab=Page; Build(); Refresh(); if (Page==TEXT("Version History") && Store.IsValid()) Store->RefreshHistory(); })];
    Root->AddSlot().AutoHeight().Padding(0,0,0,10)[Tabs];
    if (Tab==TEXT("Test Arena") || Tab==TEXT("Version History"))
    { Root->AddSlot().FillHeight(1)[SNew(SScrollBox)+SScrollBox::Slot()[SAssignNew(SpecialPage,SVerticalBox)]]; BuildSpecialPage(); }
    else
    {
        auto Toolbar=SNew(SHorizontalBox);
        Toolbar->AddSlot().AutoWidth()[SNew(SComboButton).ButtonContent()[Label(TEXT("Classes"))].OnGetMenuContent_Lambda([this] {
            auto Menu=SNew(SVerticalBox); Menu->AddSlot().AutoHeight()[Button(TEXT("All classes"),[this] { Classes.Reset(); Refresh(); })];
            if (Store.IsValid()) for (const auto& V:Array(Store->Document().Get(),TEXT("classes"))) { const auto C=V->AsObject(); const FString Id=Text(C,TEXT("id"));
                Menu->AddSlot().AutoHeight().Padding(0,4)[SNew(SCheckBox).IsChecked_Lambda([this,Id] { return Classes.Contains(Id) ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; }).OnCheckStateChanged_Lambda([this,Id](ECheckBoxState State) { if (State==ECheckBoxState::Checked) Classes.Add(Id); else Classes.Remove(Id); Refresh(); })[Label(Text(C,TEXT("name")))]]; }
            return SNew(SBox).WidthOverride(270).MaxDesiredHeight(500)[SNew(SScrollBox)+SScrollBox::Slot()[Menu]]; })];
        Toolbar->AddSlot().FillWidth(1).Padding(8,0)[SNew(SEditableTextBox).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).HintText(FText::FromString(TEXT("Search names, effects and descriptions")))
            .Text(FText::FromString(Query)).OnTextChanged_Lambda([this](const FText& V) { Query=V.ToString(); Refresh(); })];
        TArray<TPair<FString,FString>> Presets; for (const FString P:{TEXT("Overview"),TEXT("Damage"),TEXT("Healing & Protection"),TEXT("Crowd Control"),TEXT("Timing & Resources"),TEXT("Conditions"),TEXT("Changes")}) Presets.Add({P,P});
        Toolbar->AddSlot().AutoWidth()[Choice(Preset,Presets,[this](FString P) { SetPreset(P); BuildGrid(); Refresh(); })];
        Toolbar->AddSlot().AutoWidth().Padding(8,0)[SNew(SComboButton).ButtonContent()[Label(TEXT("Views / columns"))].OnGetMenuContent_Lambda([this] {
            auto Menu=SNew(SVerticalBox);
            Menu->AddSlot().AutoHeight()[Field(TEXT("Personal view name"),ViewName,[this](FString V) { ViewName=V.Left(80); })];
            Menu->AddSlot().AutoHeight()[Button(TEXT("Save view"),[this] { SaveView(false); })];
            Menu->AddSlot().AutoHeight()[Button(TEXT("Load view"),[this] { SaveView(true); })];
            Menu->AddSlot().AutoHeight()[Button(TEXT("16 px / 14 px compact"),[this] { bCompact=!bCompact; Build(); Refresh(); })];
            for (int32 I=2;I<Columns.Num();++I) { const auto C=Columns[I]; Menu->AddSlot().AutoHeight()[NumericField(C.Label+TEXT(" width (px)"),C.Width,[this,C](double V) { if (auto* Column=Columns.FindByPredicate([&](const auto& Item) { return Item.Id==C.Id; })) Column->Width=FMath::Clamp(V,90.,600.); BuildGrid(); })];
                Menu->AddSlot().AutoHeight()[Button(TEXT("Move ")+C.Label+TEXT(" left"),[this,C] { const int32 Index=Columns.IndexOfByPredicate([&](const auto& Item) { return Item.Id==C.Id; }); if (Index>2) Columns.Swap(Index,Index-1); FSlateApplication::Get().DismissAllMenus(); BuildGrid(); })];
                Menu->AddSlot().AutoHeight()[Button(TEXT("Hide ")+C.Label,[this,C] { Columns.RemoveAll([&](const auto& Item) { return Item.Id==C.Id; }); FSlateApplication::Get().DismissAllMenus(); BuildGrid(); })]; }
            return SNew(SBox).WidthOverride(340).MaxDesiredHeight(600)[SNew(SScrollBox)+SScrollBox::Slot()[Menu]]; })];
        Toolbar->AddSlot().AutoWidth()[Button(TEXT("New ability"),[this] { NewAbility(false); })];
        Toolbar->AddSlot().AutoWidth().Padding(8,0)[Button(TEXT("Inspector"),[this] { bInspector=!bInspector; })];
        Root->AddSlot().AutoHeight()[Toolbar];
        Root->AddSlot().AutoHeight().Padding(0,8)[SAssignNew(Chips,SHorizontalBox)];
        auto Workspace=SNew(SHorizontalBox);
        Workspace->AddSlot().AutoWidth().Padding(0,0,12,0)[SNew(SBox).WidthOverride(200).Visibility_Lambda([this] { return bClasses && ViewportWidth>=1500 ? EVisibility::Visible : EVisibility::Collapsed; })
            [SNew(SScrollBox)+SScrollBox::Slot()[SAssignNew(ClassBrowser,SVerticalBox)]]];
        Workspace->AddSlot().FillWidth(1)[SAssignNew(Grid,SVerticalBox)];
        Workspace->AddSlot().AutoWidth().Padding(12,0,0,0)[SNew(SBox).WidthOverride(390).Visibility_Lambda([this] { return bInspector ? EVisibility::Visible : EVisibility::Collapsed; })
            [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(.045f,.061f,.082f)).Padding(12)
                [SNew(SScrollBox)+SScrollBox::Slot()[SAssignNew(Inspector,SVerticalBox)]]]];
        Root->AddSlot().FillHeight(1)[Workspace]; BuildClasses(); BuildGrid(); BuildInspector();
    }
    Root->AddSlot().AutoHeight().Padding(0,10,0,0)[SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).ColorAndOpacity(Accent).Text_Lambda([this] {
        return FText::FromString(FString::Printf(TEXT("%d matching  |  %d selected  |  %s"),Rows.Num(),Rows.IsEmpty() ? 0 : FMath::Abs(FocusRow-AnchorRow)+1,*Notice)); })];
    Root->AddSlot().AutoHeight().Padding(0,5)[SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",10.5)).ColorAndOpacity(Muted).Text_Lambda([this] { return FText::FromString(Store.IsValid() ? Store->GetMessage() : TEXT("Workshop unavailable.")); })];
    auto Footer=SNew(SHorizontalBox);
    Footer->AddSlot().AutoWidth()[Button(TEXT("Undo"),[this] { if (Store.IsValid() && Store->Document().Undo()) Changed(); })];
    Footer->AddSlot().AutoWidth().Padding(6,0)[Button(TEXT("Redo"),[this] { if (Store.IsValid() && Store->Document().Redo()) Changed(); })];
    Footer->AddSlot().FillWidth(1)[SNew(SSpacer)];
    Footer->AddSlot().AutoWidth()[Button(TEXT("Save shared draft"),[this] { if (Store.IsValid()) Store->SaveShared(); })];
    Footer->AddSlot().AutoWidth().Padding(6,0)[Button(TEXT("Retry connection"),[this] { if (Store.IsValid()) Store->Retry(); })];
    Footer->AddSlot().AutoWidth()[Button(TEXT("Review & Publish"),[this] { Tab=TEXT("Version History"); Build(); })];
    Root->AddSlot().AutoHeight()[Footer];
}
void SWarAbilityWorkshop::Tick(const FGeometry& Geometry,double Time,float Delta)
{
    SCompoundWidget::Tick(Geometry,Time,Delta); const bool Small=ViewportWidth<1500; ViewportWidth=Geometry.GetLocalSize().X; if (Small!=(ViewportWidth<1500)) RefreshChips();
    if (Store.IsValid() && ObservedSerial!=Store->Document().Serial()) { ObservedSerial=Store->Document().Serial(); LastEditTime=Time; Refresh(); }
    if (Store.IsValid() && ObservedRemoteSerial!=Store->RemoteSerial()) { ObservedRemoteSerial=Store->RemoteSerial(); if (Tab==TEXT("Version History")) BuildSpecialPage(); }
    if (HorizontalScroll && Grid) { float Width=0; for (int32 I=2;I<Columns.Num();++I) Width+=Columns[I].Width;
        const float Available=FMath::Max(1.f,Grid->GetCachedGeometry().GetLocalSize().X-Columns[0].Width-Columns[1].Width);
        ScrollOffset=FMath::Clamp(ScrollOffset,0.f,FMath::Max(0.f,Width-Available)); HorizontalScroll->SetState(Width>0 ? ScrollOffset/Width : 0,Width>0 ? FMath::Min(1.f,Available/Width) : 1); }
    if (LastEditTime>0 && Time-LastEditTime>.8) { Store->Autosave(); LastEditTime=0; }
}
void SWarAbilityWorkshop::SetPreset(const FString& Value)
{
    Preset=Value; Columns={{TEXT("class"),TEXT("Class"),180,false},{TEXT("ability"),TEXT("Ability / component"),250,false}};
    const auto Add=[this](const TCHAR* Id,const TCHAR* Name,float Width=140,bool Numeric=false) { Columns.Add({Id,Name,Width,Numeric}); };
    if (Value==TEXT("Overview")) { Add(TEXT("level"),TEXT("Unlock level"),110,true); Add(TEXT("damage"),TEXT("Damage (base)"),150,true); Add(TEXT("heal"),TEXT("Healing (base)"),150,true); Add(TEXT("cooldown"),TEXT("Cooldown (s)"),145,true); Add(TEXT("conditions"),TEXT("Conditional rules"),380); Add(TEXT("changes"),TEXT("Overrides")); }
    else if (Value==TEXT("Damage")) { Add(TEXT("damage"),TEXT("Damage min"),150,true); Add(TEXT("damageMax"),TEXT("Damage max"),150,true); Add(TEXT("scale"),TEXT("Stat scale"),130,true); Add(TEXT("duration"),TEXT("Duration (s)"),140,true); Add(TEXT("interval"),TEXT("Tick (s)"),130,true); Add(TEXT("conditions"),TEXT("Conditional rules"),420); }
    else if (Value==TEXT("Healing & Protection")) { Add(TEXT("heal"),TEXT("Healing min"),160,true); Add(TEXT("healMax"),TEXT("Healing max"),160,true); Add(TEXT("status"),TEXT("Protection / status"),220); Add(TEXT("duration"),TEXT("Duration (s)"),150,true); Add(TEXT("conditions"),TEXT("Conditional rules"),420); }
    else if (Value==TEXT("Crowd Control")) { Add(TEXT("status"),TEXT("Control / status"),200); Add(TEXT("duration"),TEXT("Duration (s)"),140,true); Add(TEXT("magnitude"),TEXT("Magnitude"),140,true); Add(TEXT("target"),TEXT("Target")); Add(TEXT("conditions"),TEXT("Conditional rules"),420); }
    else if (Value==TEXT("Timing & Resources")) { Add(TEXT("cooldown"),TEXT("Cooldown (s)"),150,true); Add(TEXT("gcd"),TEXT("Global CD (s)"),150,true); Add(TEXT("cast"),TEXT("Cast (s)"),130,true); Add(TEXT("mana"),TEXT("Mana"),120,true); Add(TEXT("resource"),TEXT("Class cost"),140,true); Add(TEXT("range"),TEXT("Range (m)"),140,true); }
    else if (Value==TEXT("Conditions")) { Add(TEXT("conditions"),TEXT("IF → THEN"),480); Add(TEXT("checks"),TEXT("Checks"),210); Add(TEXT("subject"),TEXT("Subject"),150); Add(TEXT("source"),TEXT("Source"),160); Add(TEXT("event"),TEXT("Evaluation"),170); Add(TEXT("bonus"),TEXT("Bonus"),250); Add(TEXT("dependencies"),TEXT("Dependencies"),280); }
    else { Add(TEXT("changes"),TEXT("Override count"),170,true); Add(TEXT("paths"),TEXT("Overridden fields"),420); Add(TEXT("conditions"),TEXT("Conditional rules"),420); }
}
void SWarAbilityWorkshop::BuildClasses()
{
    if (!ClassBrowser || !Store.IsValid()) return; ClassBrowser->ClearChildren();
    ClassBrowser->AddSlot().AutoHeight()[Button(TEXT("All 24 classes"),[this] { Classes.Reset(); Refresh(); })];
    FString Realm,Race;
    for (const auto& V:Array(Store->Document().Get(),TEXT("classes")))
    {
        const auto C=V->AsObject(); const FString Id=Text(C,TEXT("id"));
        if (Realm!=Text(C,TEXT("realm"))) { Realm=Text(C,TEXT("realm")); ClassBrowser->AddSlot().AutoHeight().Padding(0,16,0,6)[Label(Realm==TEXT("aegis") ? TEXT("AEGIS ACCORD") : TEXT("RIFTBOUND HOST"))]; }
        if (Race!=Text(C,TEXT("race"))) { Race=Text(C,TEXT("race")); const TMap<FString,FString> Names{{TEXT("empire"),TEXT("Empire")},{TEXT("dwarf"),TEXT("Dwarf")},{TEXT("high_elf"),TEXT("High Elf")},{TEXT("chaos"),TEXT("Chaos")},{TEXT("greenskin"),TEXT("Greenskin")},{TEXT("dark_elf"),TEXT("Dark Elf")}}; ClassBrowser->AddSlot().AutoHeight().Padding(0,8,0,4)[Label(Names.FindRef(Race),true)]; }
        ClassBrowser->AddSlot().AutoHeight().Padding(0,4)[SNew(SCheckBox).IsChecked_Lambda([this,Id] { return Classes.Contains(Id) ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
            .OnCheckStateChanged_Lambda([this,Id](ECheckBoxState State) { if (State==ECheckBoxState::Checked) Classes.Add(Id); else Classes.Remove(Id); Refresh(); })[Label(Text(C,TEXT("name")))]];
    }
}
TSharedRef<SWidget> SWarAbilityWorkshop::FilterMenu(const FWarWorkshopColumn& C)
{
    auto Menu=SNew(SVerticalBox);
    Menu->AddSlot().AutoHeight()[Label(C.Label)];
    Menu->AddSlot().AutoHeight()[Button(TEXT("Sort ascending"),[this,C] { SortColumn=C.Id; bDescending=false; Refresh(); })];
    Menu->AddSlot().AutoHeight()[Button(TEXT("Sort descending"),[this,C] { SortColumn=C.Id; bDescending=true; Refresh(); })];
    Menu->AddSlot().AutoHeight()[Field(C.bNumber ? TEXT("=20, >=20, or 10..30; OR: 10|20") : TEXT("Contains; OR values separated by |"),Filters.FindRef(C.Id),[this,C](FString V) { if (V.IsEmpty()) Filters.Remove(C.Id); else Filters.Add(C.Id,V); Refresh(); })];
    Menu->AddSlot().AutoHeight()[Button(TEXT("Clear this filter"),[this,C] { Filters.Remove(C.Id); Refresh(); })];
    return SNew(SBox).WidthOverride(360)[Menu];
}
TSharedRef<SWidget> SWarAbilityWorkshop::Header(bool bFrozen)
{
    auto Row=SNew(SHorizontalBox);
    for (int32 I=bFrozen ? 0 : 2;I<(bFrozen ? FMath::Min(2,Columns.Num()) : Columns.Num());++I)
    { const auto C=Columns[I]; Row->AddSlot().AutoWidth()[SNew(SBox).WidthOverride(C.Width).HeightOverride(62)[SNew(SComboButton).ContentPadding(FMargin(7,5))
        .ButtonContent()[SNew(STextBlock).Text(FText::FromString(C.Label)).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).ColorAndOpacity(Ink).WrapTextAt(C.Width-40).AutoWrapText(true)]
        .OnGetMenuContent_Lambda([this,C] { return FilterMenu(C); })]]; }
    if (!bFrozen) Row->SetRenderTransform(TAttribute<TOptional<FSlateRenderTransform>>::CreateLambda([this] { return FSlateRenderTransform(FVector2D(-ScrollOffset,0)); }));
    return Row;
}
void SWarAbilityWorkshop::BuildGrid()
{
    if (!Grid) return; Grid->ClearChildren();
    auto Editing=SNew(SHorizontalBox);
    Editing->AddSlot().FillWidth(1)[SAssignNew(CellEditor,SEditableTextBox).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).HintText(FText::FromString(TEXT("F2 / double-click to edit; Shift-click for a rectangle")))
        .Text_Lambda([this] { return FText::FromString(EditValue); }).OnTextChanged_Lambda([this](const FText& V) { EditValue=V.ToString(); })
        .OnTextCommitted_Lambda([this](const FText&,ETextCommit::Type Type) { if (Type==ETextCommit::OnEnter) CommitCell(); })];
    Editing->AddSlot().AutoWidth().Padding(6,0)[Choice(BulkOperation,{{TEXT("set"),TEXT("Set")},{TEXT("add"),TEXT("Add")},{TEXT("multiply"),TEXT("Multiply")},{TEXT("reset"),TEXT("Reset to base")}},[this](FString V) { BulkOperation=V; BuildGrid(); })];
    Editing->AddSlot().AutoWidth()[Button(TEXT("Preview bulk"),[this] { PrepareEdits(BulkOperation,EditValue); })];
    Editing->AddSlot().AutoWidth().Padding(6,0)[Button(TEXT("Apply preview"),[this] { CommitEdits(); })];
    Grid->AddSlot().AutoHeight().Padding(0,0,0,8)[Editing];
    Grid->AddSlot().AutoHeight()[SNew(SHorizontalBox)+SHorizontalBox::Slot().AutoWidth()[Header(true)]
        +SHorizontalBox::Slot().FillWidth(1)[SNew(SBox).Clipping(EWidgetClipping::ClipToBounds)[Header(false)]]];
    Grid->AddSlot().FillHeight(1)[SAssignNew(List,SListView<TSharedPtr<FWarWorkshopRow>>).ListItemsSource(&Rows)
        .SelectionMode(ESelectionMode::None).OnGenerateRow(this,&SWarAbilityWorkshop::GenerateRow)];
    Grid->AddSlot().AutoHeight()[SAssignNew(HorizontalScroll,SScrollBar).Orientation(Orient_Horizontal).OnUserScrolled_Lambda([this](float Offset) { float Width=0; for (int32 I=2;I<Columns.Num();++I) Width+=Columns[I].Width; ScrollOffset=Offset*Width; })];
}
TSharedRef<SWidget> SWarAbilityWorkshop::Cells(const TSharedPtr<FWarWorkshopRow>& Row,bool bFrozen)
{
    auto LineRow=SNew(SHorizontalBox);
    for (int32 I=bFrozen ? 0 : 2;I<(bFrozen ? 2 : Columns.Num());++I)
    {
        const auto C=Columns[I]; const FString Value=Cell(*Row,C.Id),P=Path(*Row,C.Id);
        bool Overridden=false; for (const auto& V:Array(Row->Assignment,TEXT("overrides"))) if (Text(V->AsObject(),TEXT("path"))==P) Overridden=true;
        auto CellBox=SNew(SHorizontalBox);
        if (I==1 && Row->Depth==0) CellBox->AddSlot().AutoWidth()[SNew(SButton).ContentPadding(FMargin(4,0)).OnClicked_Lambda([this,Id=Row->Id] { if (Expanded.Contains(Id)) Expanded.Remove(Id); else Expanded.Add(Id); Refresh(); return FReply::Handled(); })[Label(Expanded.Contains(Row->Id) ? TEXT("−") : TEXT("+"))]];
        CellBox->AddSlot().FillWidth(1).HAlign(C.bNumber ? HAlign_Right : HAlign_Left).VAlign(VAlign_Center).Padding(I==1 ? Row->Depth*12+6 : 6,0)[SNew(STextBlock).Text(FText::FromString(Value)).Font(FCoreStyle::GetDefaultFontStyle("Regular",FontSize())).ColorAndOpacity(Overridden ? Accent : Ink).OverflowPolicy(ETextOverflowPolicy::Ellipsis)];
        if (Overridden) CellBox->AddSlot().AutoWidth()[Label(TEXT(" ◆"))];
        LineRow->AddSlot().AutoWidth()[SNew(SBox).WidthOverride(C.Width).HeightOverride(bCompact ? 32 : 36)[SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).Padding(FMargin(0,1))
            .BorderBackgroundColor_Lambda([this,Row,I] { const int32 R=Rows.IndexOfByKey(Row); return R>=FMath::Min(FocusRow,AnchorRow) && R<=FMath::Max(FocusRow,AnchorRow) && I>=FMath::Min(FocusCol,AnchorCol) && I<=FMath::Max(FocusCol,AnchorCol) ? FLinearColor(.08f,.24f,.29f) : (R%2==0 ? FLinearColor(.048f,.065f,.086f) : Panel); })
            .ToolTipText(FText::FromString(Value+(Overridden ? TEXT("\nClass override; Reset to base removes it.") : TEXT("\nInherited from shared base ability."))))
            .OnMouseButtonDown_Lambda([this,Row,I](const FGeometry&,const FPointerEvent& Event) { Select(Rows.IndexOfByKey(Row),I,Event.IsShiftDown()); return FReply::Handled().SetUserFocus(SharedThis(this),EFocusCause::Mouse); })[CellBox]]];
    }
    if (!bFrozen) LineRow->SetRenderTransform(TAttribute<TOptional<FSlateRenderTransform>>::CreateLambda([this] { return FSlateRenderTransform(FVector2D(-ScrollOffset,0)); }));
    return LineRow;
}
TSharedRef<ITableRow> SWarAbilityWorkshop::GenerateRow(TSharedPtr<FWarWorkshopRow> Row,const TSharedRef<STableViewBase>& Table)
{ return SNew(STableRow<TSharedPtr<FWarWorkshopRow>>,Table).Padding(0)[SNew(SHorizontalBox)+SHorizontalBox::Slot().AutoWidth()[Cells(Row,true)]
    +SHorizontalBox::Slot().FillWidth(1)[SNew(SBox).Clipping(EWidgetClipping::ClipToBounds)[Cells(Row,false)]]]; }

FString SWarAbilityWorkshop::Path(const FWarWorkshopRow& R,const FString& Column) const
{
    const TMap<FString,FString> Simple{{TEXT("cooldown"),TEXT("cooldownSec")},{TEXT("gcd"),TEXT("gcdSec")},{TEXT("cast"),TEXT("timing/castSec")},{TEXT("mana"),TEXT("resource/manaCost")},{TEXT("resource"),TEXT("resource/careerCost")},{TEXT("range"),TEXT("targeting/range")}};
    if (Simple.Contains(Column) && R.Depth==0) return Simple.FindRef(Column);
    TArray<TSharedPtr<FJsonObject>> Effects;
    for (const auto& V:Array(R.Ability,TEXT("effects")))
    { const auto E=V->AsObject(); if ((!R.EffectId.IsEmpty() && R.EffectId!=Text(E,TEXT("id"))) || !R.RuleId.IsEmpty()) continue;
        const FString Kind=Text(E,TEXT("kind"));
        if (((Column==TEXT("damage") || Column==TEXT("damageMax")) && Kind==TEXT("damage")) || ((Column==TEXT("heal") || Column==TEXT("healMax")) && Kind==TEXT("heal")) || ((Column==TEXT("scale")) && Object(E,TEXT("amount")))
            || ((Column==TEXT("duration") || Column==TEXT("interval")) && (Object(E,TEXT("periodic")) || Object(E,TEXT("status")) || Object(E,TEXT("playerStatus"))))
            || (Column==TEXT("magnitude") && (Object(E,TEXT("status")) || Object(E,TEXT("playerStatus"))))) Effects.Add(E); }
    if (Effects.Num()!=1) return TEXT(""); const auto E=Effects[0]; const FString Prefix=TEXT("effects/")+Text(E,TEXT("id"))+TEXT("/");
    if (Column==TEXT("damage") || Column==TEXT("heal")) return Prefix+TEXT("amount/min");
    if (Column==TEXT("damageMax") || Column==TEXT("healMax")) return Prefix+TEXT("amount/max");
    if (Column==TEXT("scale")) return Prefix+TEXT("amount/statScale");
    if (Column==TEXT("interval")) return Object(E,TEXT("periodic")) ? Prefix+TEXT("periodic/intervalSec") : TEXT("");
    return Prefix+(Object(E,TEXT("periodic")) ? TEXT("periodic/") : Object(E,TEXT("status")) ? TEXT("status/") : TEXT("playerStatus/"))+(Column==TEXT("magnitude") ? TEXT("magnitude") : TEXT("durationSec"));
}
FString SWarAbilityWorkshop::Cell(const FWarWorkshopRow& R,const FString& Column) const
{
    if (Column==TEXT("class")) return R.Depth ? TEXT("") : R.ClassName;
    if (Column==TEXT("ability")) return !R.EffectId.IsEmpty() ? Text(Find(R.Ability,TEXT("effects"),R.EffectId),TEXT("kind"))+TEXT(" · ")+R.EffectId.Left(18) : !R.RuleId.IsEmpty() ? TEXT("IF · ")+Text(Find(R.Ability,TEXT("conditions"),R.RuleId),TEXT("name")) : Text(R.Ability,TEXT("name"));
    if (Column==TEXT("level")) return R.Assignment ? N(Number(R.Assignment,TEXT("unlockLevel"))) : TEXT("—");
    if (Column==TEXT("target")) return Text(Object(R.Ability,TEXT("targeting")),TEXT("target"));
    if (Column==TEXT("changes")) return N(Array(R.Assignment,TEXT("overrides")).Num());
    if (Column==TEXT("paths")) { TArray<FString> Paths; for (const auto& V:Array(R.Assignment,TEXT("overrides"))) Paths.Add(Text(V->AsObject(),TEXT("path"))); return FString::Join(Paths,TEXT(", ")); }
    const FString P=Path(R,Column); double Value;
    if (!P.IsEmpty() && Numeric(R.Ability,P,Value)) return N(Value);
    if (Column==TEXT("damage") || Column==TEXT("heal") || Column==TEXT("damageMax") || Column==TEXT("healMax"))
    { if (!R.RuleId.IsEmpty()) return TEXT("—"); double Total=0; int32 Count=0; for (const auto& V:Array(R.Ability,TEXT("effects"))) if ((R.EffectId.IsEmpty() || Text(V->AsObject(),TEXT("id"))==R.EffectId) && Text(V->AsObject(),TEXT("kind"))==(Column.StartsWith(TEXT("damage")) ? TEXT("damage") : TEXT("heal"))) { Total+=Number(Object(V->AsObject(),TEXT("amount")),Column.EndsWith(TEXT("Max")) ? TEXT("max") : TEXT("min")); ++Count; } return Count ? N(Total) : TEXT("—"); }
    if (Column==TEXT("status")) { TArray<FString> Kinds; for (const auto& V:Array(R.Ability,TEXT("effects"))) if (R.EffectId.IsEmpty() || Text(V->AsObject(),TEXT("id"))==R.EffectId) { const auto E=V->AsObject(); for (const TCHAR* Key:{TEXT("status"),TEXT("playerStatus")}) if (Object(E,Key)) Kinds.Add(Text(Object(E,Key),TEXT("kind"))); } return Kinds.IsEmpty() ? TEXT("—") : FString::Join(Kinds,TEXT(", ")); }
    TArray<FString> Values; TSet<FString> Checks;
    for (const auto& V:Array(R.Ability,TEXT("conditions")))
    {
        const auto Rule=V->AsObject(); if (!R.RuleId.IsEmpty() && Text(Rule,TEXT("id"))!=R.RuleId) continue;
        if (Column==TEXT("event")) Checks.Add(Text(Rule,TEXT("event")));
        else if (Column==TEXT("checks") || Column==TEXT("subject") || Column==TEXT("source")) CollectChecks(Object(Rule,TEXT("condition")),Column==TEXT("checks") ? TEXT("kind") : *Column,Checks);
        else if (Column==TEXT("dependencies")) { CollectChecks(Object(Rule,TEXT("condition")),TEXT("abilityId"),Checks); CollectChecks(Object(Rule,TEXT("condition")),TEXT("effectId"),Checks); }
        else if (Column==TEXT("conditions") || Column==TEXT("bonus"))
        { TArray<FString> Actions; for (const auto& A:Array(Rule,TEXT("actions"))) { const auto Action=A->AsObject(); const FString Kind=Text(Action,TEXT("kind")); Actions.Add(Kind==TEXT("add_effect") ? TEXT("add ")+Text(Object(Action,TEXT("effect")),TEXT("kind")) : N(Number(Action,TEXT("value"))*(Kind==TEXT("percent") ? 100 : 1))+(Kind==TEXT("percent") ? TEXT("% ") : TEXT(" flat "))+Text(Action,TEXT("effectId"))); }
            Values.Add((Column==TEXT("conditions") ? TEXT("IF ")+ConditionWords(Object(Rule,TEXT("condition")))+TEXT(" → ") : TEXT(""))+FString::Join(Actions,TEXT(" + "))); }
    }
    if (!Checks.IsEmpty()) { Values=Checks.Array(); Values.Sort(); }
    return Values.IsEmpty() ? (Column==TEXT("conditions") ? TEXT("0 · unconditional") : TEXT("—")) : FString::Join(Values,TEXT("; "));
}
bool SWarAbilityWorkshop::Matches(const FWarWorkshopRow& Row) const
{
    static const TSet<FString> NumericColumns{TEXT("level"),TEXT("damage"),TEXT("damageMax"),TEXT("heal"),TEXT("healMax"),TEXT("cooldown"),TEXT("gcd"),TEXT("cast"),TEXT("mana"),TEXT("resource"),TEXT("range"),TEXT("scale"),TEXT("duration"),TEXT("interval"),TEXT("magnitude"),TEXT("changes")};
    if (!(Text(Row.Ability,TEXT("name"))+TEXT(" ")+Text(Row.Ability,TEXT("summary"))+TEXT(" ")+Row.ClassName+TEXT(" ")+Cell(Row,TEXT("conditions"))).Contains(Query)) return false;
    for (const auto& Filter:Filters)
    { const FString V=Cell(Row,Filter.Key); TArray<FString> Alternatives; Filter.Value.ParseIntoArray(Alternatives,TEXT("|")); bool Pass=false;
        for (FString Part:Alternatives) { Part.TrimStartAndEndInline(); if (NumericColumns.Contains(Filter.Key) ? NumericFilter(V,Part) : V.Contains(Part)) Pass=true; } if (!Pass) return false; }
    return true;
}
void SWarAbilityWorkshop::Refresh()
{
    if (!Store.IsValid()) return;
    const FString FocusId=Rows.IsValidIndex(FocusRow) ? Rows[FocusRow]->Id : TEXT(""); Rows.Reset(); const auto W=Store->Document().Get();
    TMap<FString,FString> Names; for (const auto& C:Array(W,TEXT("classes"))) Names.Add(Text(C->AsObject(),TEXT("id")),Text(C->AsObject(),TEXT("name")));
    if (Tab==TEXT("Class Abilities")) for (const auto& V:Array(W,TEXT("assignments")))
    {
        const auto Assignment=V->AsObject(); if (!Classes.IsEmpty() && !Classes.Contains(Text(Assignment,TEXT("classId")))) continue;
        FString Error; auto A=FWarAbilityWorkshopDocument::Effective(W,Assignment,Error); if (!A) continue;
        auto R=MakeShared<FWarWorkshopRow>(); R->Id=R->AssignmentId=Text(Assignment,TEXT("id")); R->AbilityId=Text(A,TEXT("id")); R->ClassName=Names.FindRef(Text(Assignment,TEXT("classId"))); R->Ability=A; R->Assignment=Assignment;
        if (Matches(*R)) Rows.Add(R);
    }
    else if (Tab==TEXT("Ability Library")) for (const auto& V:Array(W,TEXT("abilities")))
    { auto R=MakeShared<FWarWorkshopRow>(); R->Id=R->AbilityId=Text(V->AsObject(),TEXT("id")); R->Ability=V->AsObject(); R->ClassName=TEXT("Shared base"); if (Matches(*R)) Rows.Add(R); }
    Rows.StableSort([this](const auto& A,const auto& B) { const FString X=Cell(*A,SortColumn),Y=Cell(*B,SortColumn); const int32 C=X.IsNumeric() && Y.IsNumeric() ? (FCString::Atod(*X)<FCString::Atod(*Y) ? -1 : FCString::Atod(*X)>FCString::Atod(*Y) ? 1 : 0) : X.Compare(Y); return bDescending ? C>0 : C<0; });
    for (int32 I=Rows.Num()-1;I>=0;--I) if (Expanded.Contains(Rows[I]->Id))
    { const auto Base=Rows[I]; TArray<TSharedPtr<FWarWorkshopRow>> Children; for (const TCHAR* Collection:{TEXT("effects"),TEXT("conditions")}) for (const auto& V:Array(Base->Ability,Collection))
        { auto R=MakeShared<FWarWorkshopRow>(*Base); const FString Id=Text(V->AsObject(),TEXT("id")); R->Id+=TEXT("/")+Id; R->Depth=1; if (FString(Collection)==TEXT("effects")) R->EffectId=Id; else R->RuleId=Id; Children.Add(R); } Rows.Insert(Children,I+1); }
    const int32 Found=Rows.IndexOfByPredicate([&](const auto& R) { return R->Id==FocusId; }); FocusRow=Found==INDEX_NONE ? 0 : Found; AnchorRow=FocusRow;
    PendingEdits.Reset(); PendingSelection.Reset(); if (List) List->RequestListRefresh(); RefreshChips();
}
void SWarAbilityWorkshop::RefreshChips()
{
    if (!Chips) return; Chips->ClearChildren();
    if (ViewportWidth<1500 && Store.IsValid()) { TArray<TPair<FString,FString>> Options{{TEXT(""),TEXT("All classes")}}; for (const auto& V:Array(Store->Document().Get(),TEXT("classes"))) Options.Add({Text(V->AsObject(),TEXT("id")),Text(V->AsObject(),TEXT("name"))}); Chips->AddSlot().AutoWidth()[Choice(Classes.Num()==1 ? Classes.Array()[0] : TEXT(""),Options,[this](FString V) { Classes.Reset(); if (!V.IsEmpty()) Classes.Add(V); Refresh(); })]; }
    for (const auto& F:Filters) Chips->AddSlot().AutoWidth().Padding(0,0,6,0)[Button(F.Key+TEXT(": ")+F.Value+TEXT(" ×"),[this,Id=F.Key] { Filters.Remove(Id); Refresh(); })];
    if (Filters.IsEmpty()) Chips->AddSlot().AutoWidth()[Label(TEXT("Header filters combine with AND • choices within a filter use OR"),true)];
}
void SWarAbilityWorkshop::Select(int32 R,int32 C,bool Extend)
{
    if (!Rows.IsValidIndex(R) || !Columns.IsValidIndex(C)) return; FocusRow=R; FocusCol=C; if (!Extend) { AnchorRow=R; AnchorCol=C; }
    if (!bDirtyComposer) SetComposer(Rows[R]->AbilityId,Rows[R]->AssignmentId);
    EditValue=Cell(*Rows[R],Columns[C].Id); PendingEdits.Reset();
}
void SWarAbilityWorkshop::EditCell()
{
    if (!Rows.IsValidIndex(FocusRow)) return;
    const auto R=Rows[FocusRow]; if (R->AssignmentId.IsEmpty() || Path(*R,Columns[FocusCol].Id).IsEmpty())
    { bInspector=true; Section=R->RuleId.IsEmpty() ? TEXT("Effects") : TEXT("Conditions"); BuildInspector(); Notice=TEXT("Shared structure or aggregate: edit the component in the inspector."); return; }
    bEditingCell=true; FSlateApplication::Get().SetKeyboardFocus(CellEditor,EFocusCause::SetDirectly); CellEditor->SelectAllText();
}
void SWarAbilityWorkshop::PrepareEdits(const FString& Operation,const FString& Value)
{
    PendingEdits.Reset(); PendingSelection.Reset(); if (Rows.IsEmpty()) return;
    if (Operation!=TEXT("reset") && !Value.IsNumeric()) { Notice=TEXT("Bulk value must be numeric."); return; }
    TArray<FString> Changes;
    for (int32 R=FMath::Min(AnchorRow,FocusRow);R<=FMath::Max(AnchorRow,FocusRow);++R) for (int32 C=FMath::Min(AnchorCol,FocusCol);C<=FMath::Max(AnchorCol,FocusCol);++C)
    {
        const auto Row=Rows[R]; const FString P=Path(*Row,Columns[C].Id);
        if (Row->AssignmentId.IsEmpty() || P.IsEmpty()) { Notice=TEXT("Selection includes shared, text or aggregate cells. Select editable numeric components only."); PendingEdits.Reset(); return; }
        for (const auto& E:PendingEdits) if (E.AssignmentId==Row->AssignmentId && E.Path==P) { Notice=TEXT("Selection repeats a parent/component field; select only one of them."); PendingEdits.Reset(); return; }
        PendingEdits.Add({Row->AssignmentId,P,Operation,FCString::Atod(*Value)}); PendingSelection.Add(Row->AssignmentId);
        if (Changes.Num()<3) Changes.Add(Text(Row->Ability,TEXT("name"))+TEXT(" ")+Columns[C].Label+TEXT(": ")+Cell(*Row,Columns[C].Id)+TEXT(" → ")+Operation+TEXT(" ")+Value);
    }
    Notice=FString::Printf(TEXT("Preview: %d cells in %d visible assignments. "),PendingEdits.Num(),PendingSelection.Num())+FString::Join(Changes,TEXT("; "))+TEXT(". Apply preview commits all or none.");
}
void SWarAbilityWorkshop::CommitEdits()
{
    if (!Store.IsValid() || PendingEdits.IsEmpty()) return;
    FString Error; if (!Store->Document().EditCells(PendingEdits,PendingSelection,Error)) { Notice=Error; return; }
    Notice=TEXT("Numeric overrides applied atomically. ◆ marks a class override."); Changed();
}
void SWarAbilityWorkshop::CommitCell() { AnchorRow=FocusRow; AnchorCol=FocusCol; PrepareEdits(TEXT("set"),EditValue); CommitEdits(); bEditingCell=false; FSlateApplication::Get().SetKeyboardFocus(SharedThis(this)); }
FReply SWarAbilityWorkshop::OnMouseButtonDoubleClick(const FGeometry&,const FPointerEvent&) { EditCell(); return FReply::Handled(); }
void SWarAbilityWorkshop::Copy()
{
    if (Rows.IsEmpty()) return; TArray<FString> Lines;
    for (int32 R=FMath::Min(AnchorRow,FocusRow);R<=FMath::Max(AnchorRow,FocusRow);++R) { TArray<FString> Values; for (int32 C=FMath::Min(AnchorCol,FocusCol);C<=FMath::Max(AnchorCol,FocusCol);++C) Values.Add(Cell(*Rows[R],Columns[C].Id)); Lines.Add(FString::Join(Values,TEXT("\t"))); }
    FPlatformApplicationMisc::ClipboardCopy(*FString::Join(Lines,TEXT("\n"))); Notice=TEXT("Rectangle copied as tab-separated values.");
}
void SWarAbilityWorkshop::Paste()
{
    FString TextValue; FPlatformApplicationMisc::ClipboardPaste(TextValue); if (TextValue.Len()>1000000) { Notice=TEXT("Clipboard exceeds 1 MB."); return; }
    TextValue.ReplaceInline(TEXT("\r"),TEXT("")); TextValue.TrimEndInline(); TArray<FString> Lines; TextValue.ParseIntoArray(Lines,TEXT("\n"),false);
    PendingEdits.Reset(); PendingSelection.Reset(); int32 Width=-1;
    for (int32 R=0;R<Lines.Num();++R) { TArray<FString> Values; Lines[R].ParseIntoArray(Values,TEXT("\t"),false); if (Width<0) Width=Values.Num();
        if (Width!=Values.Num() || !Rows.IsValidIndex(FocusRow+R) || !Columns.IsValidIndex(FocusCol+Width-1)) { Notice=TEXT("Paste must be rectangular and fit visible rows and columns."); PendingEdits.Reset(); return; }
        for (int32 C=0;C<Values.Num();++C) { const auto Row=Rows[FocusRow+R]; const FString P=Path(*Row,Columns[FocusCol+C].Id);
            if (!Values[C].IsNumeric() || P.IsEmpty() || Row->AssignmentId.IsEmpty()) { Notice=TEXT("Paste contains nonnumeric, aggregate or shared cells. Nothing changed."); PendingEdits.Reset(); return; }
            PendingEdits.Add({Row->AssignmentId,P,TEXT("set"),FCString::Atod(*Values[C])}); PendingSelection.Add(Row->AssignmentId); }
    }
    Notice=FString::Printf(TEXT("Paste preview: %d numeric cells / %d visible assignments. Apply preview to commit."),PendingEdits.Num(),PendingSelection.Num());
}
void SWarAbilityWorkshop::FillDown()
{
    PendingEdits.Reset(); PendingSelection.Reset(); const int32 First=FMath::Min(AnchorRow,FocusRow),Last=FMath::Max(AnchorRow,FocusRow);
    if (!Rows.IsValidIndex(First) || First==Last) { Notice=TEXT("Select at least two rows to fill down."); return; }
    for (int32 C=FMath::Min(AnchorCol,FocusCol);C<=FMath::Max(AnchorCol,FocusCol);++C)
    {
        const FString Value=Cell(*Rows[First],Columns[C].Id);
        for (int32 R=First+1;R<=Last;++R)
        {
            const auto Row=Rows[R]; const FString P=Path(*Row,Columns[C].Id);
            if (!Value.IsNumeric() || P.IsEmpty() || Row->AssignmentId.IsEmpty()) { PendingEdits.Reset(); Notice=TEXT("Fill down requires numeric component cells in every selected column."); return; }
            if (PendingEdits.ContainsByPredicate([&](const auto& E) { return E.AssignmentId==Row->AssignmentId && E.Path==P; })) { PendingEdits.Reset(); Notice=TEXT("Select only one occurrence of each component field."); return; }
            PendingEdits.Add({Row->AssignmentId,P,TEXT("set"),FCString::Atod(*Value)}); PendingSelection.Add(Row->AssignmentId);
        }
    }
    Notice=FString::Printf(TEXT("Fill preview: %d cells. Each column uses its own top value. Apply preview to commit."),PendingEdits.Num());
}
FReply SWarAbilityWorkshop::OnKeyDown(const FGeometry&,const FKeyEvent& Event)
{
    const FKey K=Event.GetKey();
    if (K==EKeys::Escape) { bEditingCell=false; PendingEdits.Reset(); Notice=TEXT("Edit cancelled."); FSlateApplication::Get().SetKeyboardFocus(SharedThis(this)); return FReply::Handled(); }
    if (Event.IsControlDown())
    {
        if (K==EKeys::C) Copy(); else if (K==EKeys::V) Paste();
        else if (K==EKeys::Z) { if (Store.IsValid() && Store->Document().Undo()) Changed(); }
        else if (K==EKeys::Y) { if (Store.IsValid() && Store->Document().Redo()) Changed(); }
        else if (K==EKeys::D) FillDown();
        else return FReply::Unhandled(); return FReply::Handled();
    }
    if (K==EKeys::F2) { EditCell(); return FReply::Handled(); }
    if (K==EKeys::Enter && bEditingCell) { CommitCell(); return FReply::Handled(); }
    int32 R=FocusRow,C=FocusCol;
    if (K==EKeys::Down || K==EKeys::Enter) ++R; else if (K==EKeys::Up) --R; else if (K==EKeys::Right || K==EKeys::Tab) C+=Event.IsShiftDown() && K==EKeys::Tab ? -1 : 1; else if (K==EKeys::Left) --C; else return FReply::Unhandled();
    if (C>=Columns.Num()) { C=0; ++R; } if (C<0) { C=Columns.Num()-1; --R; }
    Select(FMath::Clamp(R,0,FMath::Max(0,Rows.Num()-1)),C,Event.IsShiftDown() && K!=EKeys::Tab); if (List && Rows.IsValidIndex(FocusRow)) List->RequestScrollIntoView(Rows[FocusRow]); return FReply::Handled();
}
void SWarAbilityWorkshop::Changed()
{ LastEditTime=FSlateApplication::Get().GetCurrentTime(); Refresh(); if (!bDirtyComposer && !SelectedAbility.IsEmpty()) SetComposer(SelectedAbility,SelectedAssignment); }
void SWarAbilityWorkshop::SaveView(bool Load)
{
    if (ViewName.IsEmpty()) return; const FString Key=TEXT("View.")+ViewName; FString Json;
    if (Load)
    {
        if (!GConfig->GetString(TEXT("AegisWar.AbilityWorkshop"),*Key,Json,GGameUserSettingsIni)) { Notice=TEXT("No saved view with that name."); return; }
        const auto V=Parse(Json); if (!V) return; Query=Text(V,TEXT("query")); SortColumn=Text(V,TEXT("sort")); V->TryGetBoolField(TEXT("descending"),bDescending); V->TryGetBoolField(TEXT("compact"),bCompact);
        Filters.Reset(); const auto F=Object(V,TEXT("filters")); if (F) for (const auto& Pair:F->Values) Filters.Add(FString(Pair.Key),Pair.Value->AsString());
        Classes.Reset(); for (const auto& C:Array(V,TEXT("classes"))) Classes.Add(C->AsString());
        SetPreset(Text(V,TEXT("preset"))); const auto Defaults=Columns; Columns.SetNum(2);
        for (const auto& C:Array(V,TEXT("columns"))) { const auto J=C->AsObject(); const auto* Existing=Defaults.FindByPredicate([&](const auto& D) { return D.Id==Text(J,TEXT("id")); }); if (Existing && Existing->Id!=TEXT("class") && Existing->Id!=TEXT("ability")) { auto D=*Existing; D.Width=FMath::Clamp(Number(J,TEXT("width")),90.,600.); Columns.Add(D); } }
        Build(); Refresh(); Notice=TEXT("Personal view restored.");
    }
    else
    {
        auto V=MakeShared<FJsonObject>(); V->SetStringField(TEXT("query"),Query); V->SetStringField(TEXT("sort"),SortColumn); V->SetStringField(TEXT("preset"),Preset); V->SetBoolField(TEXT("descending"),bDescending); V->SetBoolField(TEXT("compact"),bCompact);
        auto F=MakeShared<FJsonObject>(); for (const auto& Pair:Filters) F->SetStringField(Pair.Key,Pair.Value); V->SetObjectField(TEXT("filters"),F);
        TArray<TSharedPtr<FJsonValue>> SavedClasses,SavedColumns; for (const auto& C:Classes) SavedClasses.Add(MakeShared<FJsonValueString>(C));
        for (const auto& C:Columns) { auto J=MakeShared<FJsonObject>(); J->SetStringField(TEXT("id"),C.Id); J->SetNumberField(TEXT("width"),C.Width); SavedColumns.Add(MakeShared<FJsonValueObject>(J)); }
        V->SetArrayField(TEXT("classes"),SavedClasses); V->SetArrayField(TEXT("columns"),SavedColumns); GConfig->SetString(TEXT("AegisWar.AbilityWorkshop"),*Key,*Serialize(V),GGameUserSettingsIni); GConfig->Flush(false,GGameUserSettingsIni); Notice=TEXT("Personal view saved.");
    }
}

bool SWarAbilityWorkshop::VerifyInteractions(FString& Error)
{
    if (!Store.IsValid() || Rows.Num()<2) { Error=TEXT("Workshop catalog did not load."); return false; }
    const FString Before=Serialize(Store->Document().Get());
    const FString Id=Rows[0]->AssignmentId;
    const int32 Cooldown=Columns.IndexOfByPredicate([](const auto& C) { return C.Id==TEXT("cooldown"); });
    Select(0,Cooldown,false); Select(1,Cooldown,true); PrepareEdits(TEXT("set"),TEXT("42"));
    if (PendingEdits.Num()!=2) { Error=TEXT("Visible rectangle did not preview exactly two cells."); return false; }
    CommitEdits(); FString CompileError; const auto A=FWarAbilityWorkshopDocument::Effective(Store->Document().Get(),Find(Store->Document().Get(),TEXT("assignments"),Id),CompileError);
    if (Number(A,TEXT("cooldownSec"))!=42 || !Store->Document().Undo() || Serialize(Store->Document().Get())!=Before)
    { Error=TEXT("Atomic numeric edit / undo failed."); return false; }
    if (!Store->Document().Redo()) { Error=TEXT("Redo failed."); return false; } Store->Document().Undo(); Refresh();
    Filters.Add(TEXT("class"),Rows[0]->ClassName); Filters.Add(TEXT("cooldown"),TEXT(">=0")); Refresh();
    if (Rows.Num()!=10) { Error=TEXT("Combined class/numeric filters failed."); return false; }
    const auto VisibleColumns=Columns; Columns.RemoveAt(Cooldown); Refresh();
    const bool HiddenFilterWorked=Rows.Num()==10; Columns=VisibleColumns;
    if (!HiddenFilterWorked) { Error=TEXT("Hiding a numeric column changed filter semantics."); return false; }
    Filters.Reset(); Refresh();
    auto Large=Clone(Store->Document().Get()),Template=Clone(Array(Large,TEXT("abilities"))[0]->AsObject());
    Template->SetObjectField(TEXT("resource"),Parse(TEXT(R"({"manaCost":0,"careerCost":0,"careerBuild":0})")));
    TArray<TSharedPtr<FJsonValue>> Definitions,Assignments;
    for (int32 I=0;I<209;++I)
    {
        auto Definition=Clone(Template); const FString AbilityId=FString::Printf(TEXT("proof.load_%d"),I); Definition->SetStringField(TEXT("id"),AbilityId); Definitions.Add(MakeShared<FJsonValueObject>(Definition));
        for (const auto& C:Array(Large,TEXT("classes"))) if (Assignments.Num()<5000)
        {
            auto Assignment=Parse(TEXT(R"({"unlockLevel":1,"displayOrder":0,"overrides":[],"presentations":{}})"));
            const FString ClassId=Text(C->AsObject(),TEXT("id")); Assignment->SetStringField(TEXT("id"),ClassId+TEXT(":")+AbilityId); Assignment->SetStringField(TEXT("classId"),ClassId); Assignment->SetStringField(TEXT("abilityId"),AbilityId); Assignment->SetNumberField(TEXT("displayOrder"),I); Assignments.Add(MakeShared<FJsonValueObject>(Assignment));
        }
    }
    Large->SetArrayField(TEXT("abilities"),Definitions); Large->SetArrayField(TEXT("assignments"),Assignments);
    if (!Store->Document().Load(Serialize(Large),Error)) return false; Refresh();
    const bool Loaded5000=Rows.Num()==5000;
    if (!Store->Document().Load(Before,Error)) return false; Refresh();
    if (!Loaded5000) { Error=TEXT("Virtualized 5,000-assignment catalog did not load."); return false; }
    SetComposer(Rows[0]->AbilityId,Rows[0]->AssignmentId); Section=TEXT("Conditions"); bInspector=true;
    const auto E=Array(Composer,TEXT("effects"))[0]->AsObject();
    auto Rule=Parse(TEXT("{\"id\":\"proof_bonus\",\"name\":\"Lingering damage synergy\",\"event\":\"application\",\"condition\":{\"kind\":\"all\",\"children\":[{\"kind\":\"dot\",\"subject\":\"recipient\",\"source\":\"self\"}]},\"actions\":[{\"kind\":\"percent\",\"value\":0.25}]}"));
    Array(Rule,TEXT("actions"))[0]->AsObject()->SetStringField(TEXT("effectId"),Text(E,TEXT("id")));
    Composer->SetArrayField(TEXT("conditions"),{MakeShared<FJsonValueObject>(Rule)}); bDirtyComposer=true; BuildInspector();
    Notice=TEXT("Proof: filters, atomic edits, undo/redo and 5,000 assignments passed. Uncommitted example rule shown.");
    return true;
}
