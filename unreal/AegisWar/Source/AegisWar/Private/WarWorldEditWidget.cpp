#include "WarWorldEditWidget.h"
#include "WarUiArtwork.h"
#include "WarWorldEditSubsystem.h"
#include "WarDevelopmentAccount.h"
#include "Engine/GameInstance.h"
#include "WarWorldEditPlacement.h"
#include "WarWorldEditCatalog.h"
#include "WarInterfaceStyle.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "Engine/World.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "GameFramework/Pawn.h"
#include "DrawDebugHelpers.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Framework/Application/SlateApplication.h"
#include "Application/ThrottleManager.h"
#include "UObject/ConstructorHelpers.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SSearchBox.h"
#include "Widgets/Input/SNumericEntryBox.h"
#include "Widgets/Layout/SExpandableArea.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"

UWarWorldEditWidget::UWarWorldEditWidget(const FObjectInitializer& Initializer) : Super(Initializer)
{
    // A hard reference retains the preview material in cooked builds.
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
    PreviewMaterial = Material.Object;
}

TSharedRef<SWidget> UWarWorldEditWidget::RebuildWidget()
{
    const TWeakObjectPtr<UWarWorldEditWidget> Weak(this);
    auto Body = SNew(SVerticalBox);
    Body->AddSlot().AutoHeight()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold", 24)).Text(FText::FromString(TEXT("City Builder")))];
    Body->AddSlot().AutoHeight().Padding(0, 8)[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).AutoWrapText(true).Text(FText::FromString(TEXT("WASD move / right-drag orbit / click to place or select")))];
    auto Commands = SNew(SHorizontalBox);
    const auto Button = [](const FString& Label, TFunction<FReply()> Action) -> TSharedRef<SWidget> {
        return SNew(SButton).IsFocusable(false).ButtonStyle(&WarInterfaceStyle::Button()).OnClicked_Lambda(MoveTemp(Action))[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 17)).Text(FText::FromString(Label))];
    };
    Commands->AddSlot().AutoWidth()[Button(TEXT("Close"), [Weak] { if (Weak.IsValid()) if (auto* P = Cast<AWarPlayerController>(Weak->GetOwningPlayer())) P->ToggleWorldEditor(); return FReply::Handled(); })];
    Commands->AddSlot().AutoWidth()[Button(TEXT("Select nearest"), [Weak] { if (Weak.IsValid()) Weak->SelectNearest(); return FReply::Handled(); })];
    for (const bool bRedo : { false, true })
        Commands->AddSlot().AutoWidth()[Button(bRedo ? TEXT("Redo") : TEXT("Undo"), [Weak, bRedo] {
            if (Weak.IsValid()) if (auto* P = Cast<AWarPlayerController>(Weak->GetOwningPlayer()))
                if (auto* E = Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>()) P->ServerWorldEditHistory(bRedo, E->GetHistory().GetRevision());
            return FReply::Handled(); })];
    Body->AddSlot().AutoHeight().Padding(0, 8)[Commands];
    Body->AddSlot().AutoHeight()[Button(TEXT("Publish draft to local game"), [Weak] {
        if (Weak.IsValid()) if (auto* P = Cast<AWarPlayerController>(Weak->GetOwningPlayer()))
            if (auto* E = Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>())
                P->ServerPublishWorldDraft(E->GetHistory().GetRevision());
        return FReply::Handled(); })];
    Body->AddSlot().AutoHeight()[SNew(STextBlock).AutoWrapText(true).Text(FText::FromString(
        TEXT("Local publishing persists this layout across launches.")))];
    auto Remote = SNew(SVerticalBox);
    Remote->AddSlot().AutoHeight()[Button(TEXT("Developer sign-in"), [Weak] {
        if (Weak.IsValid()) if (auto* A = Weak->GetGameInstance()->GetSubsystem<UWarDevelopmentAccount>()) A->BeginLogin();
        return FReply::Handled(); })];
    Remote->AddSlot().AutoHeight()[SNew(STextBlock).AutoWrapText(true).Text_Lambda([Weak] {
        const auto* A = Weak.IsValid() ? Weak->GetGameInstance()->GetSubsystem<UWarDevelopmentAccount>() : nullptr;
        return A ? FText::FromString(A->GetStatus()) : FText::GetEmpty(); })];
    for (const bool bPublish : { false, true })
        Remote->AddSlot().AutoHeight()[Button(bPublish ? TEXT("Publish remote / retry") : TEXT("Sync: pull remote (back up local)"), [Weak, bPublish] {
            if (Weak.IsValid()) if (auto* E = Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>())
            { Weak->CancelPlacement(); E->SyncRemote(Weak->GetOwningPlayer(), bPublish); }
            return FReply::Handled(); })];
    Remote->AddSlot().AutoHeight()[SNew(STextBlock).AutoWrapText(true).Text_Lambda([Weak] {
        const auto* E = Weak.IsValid() ? Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>() : nullptr;
        return E ? FText::FromString(E->GetRemoteStatus()) : FText::GetEmpty(); })];
    Body->AddSlot().AutoHeight()[SNew(SExpandableArea).InitiallyCollapsed(true).AllowAnimatedTransition(false)
        .AreaTitle(FText::FromString(TEXT("Remote world sync"))).BodyContent()[Remote]];
    Body->AddSlot().AutoHeight()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).AutoWrapText(true).Text_Lambda([Weak] {
        const auto* P = Weak.IsValid() ? Cast<AWarPlayerController>(Weak->GetOwningPlayer()) : nullptr;
        return P ? FText::FromString(P->GetWorldEditMessage()) : FText::GetEmpty(); })];
    Body->AddSlot().AutoHeight()[Button(TEXT("Cancel placement"), [Weak] {
        if (Weak.IsValid()) Weak->CancelPlacement(); return FReply::Handled(); })];
    auto Travel = SNew(SHorizontalBox);
    Travel->AddSlot().FillWidth(1)[Button(TEXT("Fly / walk"), [Weak] {
        if (Weak.IsValid()) if (auto* P = Cast<AWarPlayerController>(Weak->GetOwningPlayer()))
            if (auto* C = Cast<AWarCharacter>(P->GetPawn())) P->ServerSetDevelopmentTraversal(!C->IsDevelopmentFlying(), C->GetDevelopmentSpeed());
        return FReply::Handled(); })];
    Travel->AddSlot().FillWidth(1)[Button(TEXT("Arrival"), [Weak] {
        if (Weak.IsValid()) if (auto* P = Cast<AWarPlayerController>(Weak->GetOwningPlayer())) P->ServerReturnToDevelopmentSpawn();
        return FReply::Handled(); })];
    for (const float Step : { -0.25f, 0.25f })
        Travel->AddSlot().FillWidth(1)[Button(Step < 0 ? TEXT("Speed -") : TEXT("Speed +"), [Weak, Step] {
            if (Weak.IsValid()) if (auto* P = Cast<AWarPlayerController>(Weak->GetOwningPlayer()))
                if (auto* C = Cast<AWarCharacter>(P->GetPawn())) P->ServerSetDevelopmentTraversal(C->IsDevelopmentFlying(),
                    FMath::Clamp(C->GetDevelopmentSpeed() + Step, 0.25f, 6.f));
            return FReply::Handled(); })];
    Body->AddSlot().AutoHeight()[Travel];
    Body->AddSlot().AutoHeight().Padding(0, 4)[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).Text_Lambda([Weak] {
        const auto* C = Weak.IsValid() ? Cast<AWarCharacter>(Weak->GetOwningPlayerPawn()) : nullptr;
        return C ? FText::FromString(FString::Printf(TEXT("%s  %.2fx — flight: E up / Q down"),
            C->IsDevelopmentFlying() ? TEXT("Flying") : TEXT("Walking"), C->GetDevelopmentSpeed())) : FText::GetEmpty(); })];
    Body->AddSlot().AutoHeight()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).Text_Lambda([Weak] {
        return Weak.IsValid() ? FText::FromString(FString::Printf(TEXT("Place a model (%d / %d):"), Weak->CatalogMatches, Weak->CatalogTotal)) : FText::GetEmpty(); })];
    Body->AddSlot().AutoHeight()[SNew(SSearchBox).InitialText(FText::FromString(CatalogSearch))
        .HintText(FText::FromString(TEXT("Find a model to place")))
        .OnTextChanged_Lambda([Weak](const FText& Text) { if (Weak.IsValid()) { Weak->CatalogSearch = Text.ToString(); Weak->RefreshCatalog(); } })];
    Body->AddSlot().AutoHeight().Padding(0, 6)[SNew(SBox).HeightOverride(130)[SNew(SScrollBox)
        + SScrollBox::Slot()[SAssignNew(CatalogRows, SVerticalBox)]]];
    Body->AddSlot().AutoHeight()[SNew(SSearchBox).InitialText(FText::FromString(Search)).HintText(FText::FromString(TEXT("Find a placed building")))
        .OnTextChanged_Lambda([Weak](const FText& Text) { if (Weak.IsValid()) { Weak->Search = Text.ToString(); Weak->RefreshRows(); } })];
    Body->AddSlot().AutoHeight().Padding(0, 8)[SNew(SBox).HeightOverride(120)[SNew(SScrollBox) + SScrollBox::Slot()[SAssignNew(Rows, SVerticalBox)]]];
    Body->AddSlot().AutoHeight()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 17)).AutoWrapText(true).Text_Lambda([Weak] {
        if (!Weak.IsValid()) return FText::GetEmpty();
        auto* E = Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
        const auto* Row = E ? E->GetHistory().Find(Weak->Selected) : nullptr;
        if (!Row) return FText::FromString(TEXT("Select a building to edit."));
        const FVector P = Row->Transform.GetLocation();
        return FText::FromString(FString::Printf(TEXT("%s%s\nX %.1f m   Y %.1f m   Z %.1f m"), *Row->Id.ToString(),
            Row->bHidden ? TEXT(" (hidden)") : TEXT(""), P.X / 100, P.Y / 100, P.Z / 100)); })];
    auto ExactFields = SNew(SVerticalBox);
    const TCHAR* Labels[] = { TEXT("X m"), TEXT("Y m"), TEXT("Z m"), TEXT("Pitch"), TEXT("Yaw"), TEXT("Roll"), TEXT("Scale X"), TEXT("Scale Y"), TEXT("Scale Z") };
    for (int32 Group = 0; Group < 3; ++Group)
    {
        auto Fields = SNew(SHorizontalBox);
        for (int32 Axis = 0; Axis < 3; ++Axis)
        {
            const int32 Field = Group * 3 + Axis;
            Fields->AddSlot().FillWidth(1).Padding(2)[SNew(SNumericEntryBox<double>).AllowSpin(false)
                .Font(FCoreStyle::GetDefaultFontStyle("Regular", 15)).MinDesiredValueWidth(55)
                .ToolTipText(FText::FromString(TEXT("Press Enter to apply. Position: metres; rotation: degrees; scale: positive magnitude.")))
                .Label()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 14)).Text(FText::FromString(Labels[Field]))]
                .Value_Lambda([Weak, Field]() -> TOptional<double> {
                    const auto* E = Weak.IsValid() ? Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>() : nullptr;
                    const auto* Row = E ? E->GetHistory().Find(Weak->Selected) : nullptr;
                    return Row ? WarWorldEditPlacement::ComponentValue(Row->Transform, Field) : TOptional<double>(); })
                .OnValueCommitted_Lambda([Weak, Field](double Value, ETextCommit::Type Commit) {
                    // Losing focus never applies a partial entry to a newly selected building.
                    if (Weak.IsValid() && Commit == ETextCommit::OnEnter) Weak->SetSelectedComponent(Field, Value); })];
        }
        ExactFields->AddSlot().AutoHeight()[Fields];
    }
    Body->AddSlot().AutoHeight()[SNew(SExpandableArea).InitiallyCollapsed(true).AllowAnimatedTransition(false)
        .AreaTitleFont(FCoreStyle::GetDefaultFontStyle("Regular", 16))
        .AreaTitle(FText::FromString(TEXT("Exact transform - Enter to apply")))
        .BodyContent()[ExactFields]];
    auto Repeated = SNew(SVerticalBox);
    auto RowOptions = SNew(SHorizontalBox);
    RowOptions->AddSlot().FillWidth(1)[SNew(SNumericEntryBox<int32>).MinValue(2).MaxValue(32).AllowSpin(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",15))
        .Label()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",14)).Text(FText::FromString(TEXT("Pieces")))]
        .Value_Lambda([Weak]() -> TOptional<int32> { return Weak.IsValid() ? Weak->RowCount : 3; })
        .OnValueChanged_Lambda([Weak](int32 Value) { if (Weak.IsValid()) Weak->RowCount=FMath::Clamp(Value,2,32); })];
    RowOptions->AddSlot().FillWidth(1)[SNew(SNumericEntryBox<double>).MinValue(0).MaxValue(100).AllowSpin(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",15))
        .Label()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",14)).Text(FText::FromString(TEXT("Gap m")))]
        .Value_Lambda([Weak]() -> TOptional<double> { return Weak.IsValid() ? Weak->RowGapMeters : 0; })
        .OnValueChanged_Lambda([Weak](double Value) { if (Weak.IsValid() && FMath::IsFinite(Value)) Weak->RowGapMeters=FMath::Clamp(Value,0.,100.); })];
    RowOptions->AddSlot().AutoWidth()[SNew(SButton).IsFocusable(false).OnClicked_Lambda([Weak] {
        if (Weak.IsValid()) Weak->bRowAlongY=!Weak->bRowAlongY; return FReply::Handled(); })
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular",15)).Text_Lambda([Weak] { return FText::FromString(Weak.IsValid() && Weak->bRowAlongY ? TEXT("Local Y") : TEXT("Local X")); })]];
    Repeated->AddSlot().AutoHeight()[RowOptions];
    Repeated->AddSlot().AutoHeight()[Button(TEXT("Place row of selected model"),[Weak] {
        if (Weak.IsValid()) if (auto* P=Cast<AWarPlayerController>(Weak->GetOwningPlayer()))
            if (const auto* E=Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>())
                P->ServerCreateWorldRow(Weak->Selected,Weak->RowCount,Weak->bRowAlongY,Weak->RowGapMeters*100,
                    Weak->GridCentimeters(),E->GetHistory().GetRevision());
        return FReply::Handled(); })];
    Body->AddSlot().AutoHeight()[SAssignNew(RepeatedSection,SExpandableArea).InitiallyCollapsed(true).AllowAnimatedTransition(false)
        .AreaTitleFont(FCoreStyle::GetDefaultFontStyle("Regular",16)).AreaTitle(FText::FromString(TEXT("Repeated construction")))
        .BodyContent()[Repeated]];
    auto Snapping = SNew(SHorizontalBox);
    Snapping->AddSlot().FillWidth(1)[Button(TEXT("Grid step"), [Weak] {
        if (Weak.IsValid()) Weak->GridIndex = (Weak->GridIndex + 1) % 5;
        return FReply::Handled(); })];
    Snapping->AddSlot().FillWidth(1)[Button(TEXT("Turn step"), [Weak] {
        if (Weak.IsValid()) Weak->AngleIndex = (Weak->AngleIndex + 1) % 3;
        return FReply::Handled(); })];
    Snapping->AddSlot().FillWidth(1)[Button(TEXT("Snap XY / yaw"), [Weak] {
        if (Weak.IsValid()) Weak->SnapSelected(); return FReply::Handled(); })];
    Body->AddSlot().AutoHeight().Padding(0, 4)[Snapping];
    Body->AddSlot().AutoHeight()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).Text_Lambda([Weak] {
        if (!Weak.IsValid()) return FText::GetEmpty();
        const double Grid = Weak->GridCentimeters();
        return FText::FromString(FString::Printf(TEXT("Grid %s — move %.2fm / turn %.0f°"),
            Grid > 0 ? *FString::Printf(TEXT("%.2fm"), Grid / 100) : TEXT("off"),
            (Grid > 0 ? Grid : 100) / 100, Weak->AngleDegrees())); })];
    auto Move = SNew(SHorizontalBox);
    for (int32 Axis = 0; Axis < 3; ++Axis) for (const int32 Sign : { -1, 1 })
        Move->AddSlot().FillWidth(1)[Button(FString::Printf(TEXT("%c %s"), TEXT('X') + Axis, Sign < 0 ? TEXT("-") : TEXT("+")), [Weak, Axis, Sign] {
            if (Weak.IsValid()) { FVector Offset = FVector::ZeroVector;
                Offset[Axis] = Sign * (Weak->GridCentimeters() > 0 ? Weak->GridCentimeters() : 100); Weak->EditSelected(Offset); }
            return FReply::Handled(); })];
    Body->AddSlot().AutoHeight().Padding(0, 8)[Move];
    auto Transform = SNew(SHorizontalBox);
    for (const int32 Sign : { -1, 1 })
    {
        Transform->AddSlot().FillWidth(1)[Button(Sign < 0 ? TEXT("Turn -") : TEXT("Turn +"), [Weak, Sign] {
            if (Weak.IsValid()) Weak->EditSelected(FVector::ZeroVector, Sign * Weak->AngleDegrees()); return FReply::Handled(); })];
        Transform->AddSlot().FillWidth(1)[Button(Sign < 0 ? TEXT("Smaller") : TEXT("Larger"), [Weak, Sign] {
            if (Weak.IsValid()) Weak->EditSelected(FVector::ZeroVector, 0, Sign < 0 ? 1 / 1.1 : 1.1); return FReply::Handled(); })];
    }
    Body->AddSlot().AutoHeight()[Transform];
    Body->AddSlot().AutoHeight().Padding(0, 4)[Button(TEXT("Drop to surface"), [Weak] {
        if (Weak.IsValid()) if (auto* P = Cast<AWarPlayerController>(Weak->GetOwningPlayer()))
            if (const auto* E = Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>())
                P->ServerDropWorldObject(Weak->Selected, E->GetHistory().GetRevision());
        return FReply::Handled(); })];
    auto Storage = SNew(SHorizontalBox);
    Storage->AddSlot().FillWidth(1)[Button(TEXT("Hide / restore"), [Weak] {
        if (Weak.IsValid()) Weak->EditSelected(FVector::ZeroVector, 0, 1, true); return FReply::Handled(); })];
    for (const bool bLoad : { false, true })
        Storage->AddSlot().FillWidth(1)[Button(bLoad ? TEXT("Load draft") : TEXT("Save draft"), [Weak, bLoad] {
            if (Weak.IsValid()) if (auto* P = Cast<AWarPlayerController>(Weak->GetOwningPlayer()))
                if (auto* E = Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>()) P->ServerWorldEditDraft(bLoad, E->GetHistory().GetRevision());
            return FReply::Handled(); })];
    Body->AddSlot().AutoHeight().Padding(0, 8)[Storage];
    auto Extra = SNew(SHorizontalBox);
    Extra->AddSlot().FillWidth(1)[Button(TEXT("Duplicate"),[Weak] {
        if (Weak.IsValid()) if (auto* P=Cast<AWarPlayerController>(Weak->GetOwningPlayer()))
            if (const auto* E=Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>()) P->ServerDuplicateWorldObject(Weak->Selected,E->GetHistory().GetRevision());
        return FReply::Handled(); })];
    Extra->AddSlot().FillWidth(1)[Button(TEXT("Measure"),[Weak] {
        if (Weak.IsValid()) if (auto* P=Cast<AWarPlayerController>(Weak->GetOwningPlayer())) P->MeasureWorldObject(Weak->Selected);
        return FReply::Handled(); })];
    Extra->AddSlot().FillWidth(1)[SNew(SButton).IsFocusable(false).ButtonStyle(&WarInterfaceStyle::Button())
        .Text_Lambda([Weak] { return FText::FromString(Weak.IsValid() && Weak->ResetConfirmationRevision!=INDEX_NONE ? TEXT("Confirm reset") : TEXT("Reset to authored")); })
        .OnClicked_Lambda([Weak] {
            if (Weak.IsValid()) if (auto* P=Cast<AWarPlayerController>(Weak->GetOwningPlayer()))
                if (const auto* E=Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>())
                {
                    if (Weak->ResetConfirmationRevision==E->GetHistory().GetRevision()) { P->ServerResetWorldDraft(Weak->ResetConfirmationRevision);Weak->ResetConfirmationRevision=INDEX_NONE; }
                    else Weak->ResetConfirmationRevision=E->GetHistory().GetRevision();
                }
            return FReply::Handled(); })];
    Body->AddSlot().AutoHeight().Padding(0,6)[Extra];

    RefreshCatalog(); RefreshRows();
    if (Selected.IsNone()) SelectNearest();
    return SNew(SBox).WidthOverride(560)[SNew(SWarArtWindow)[SNew(SScrollBox)+SScrollBox::Slot()[Body]]];
}

void UWarWorldEditWidget::ExpandRepeatedConstruction()
{ if (RepeatedSection) RepeatedSection->SetExpanded(true); }

void UWarWorldEditWidget::RefreshRows()
{
    if (!Rows || !GetWorld()) return;
    Rows->ClearChildren();
    const auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); if (!E) return;
    DisplayedRevision = E->GetHistory().GetRevision();
    for (const auto& Row : E->GetHistory().GetObjects())
    {
        if (!Search.IsEmpty() && !Row.Id.ToString().Contains(Search)) continue;
        Rows->AddSlot().AutoHeight().Padding(0, 2)[SNew(SButton).IsFocusable(false)
            .OnClicked_Lambda([Weak = TWeakObjectPtr<UWarWorldEditWidget>(this), Id = Row.Id] { if (Weak.IsValid()) Weak->SelectObject(Id); return FReply::Handled(); })
            [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 17)).Text(FText::FromString(Row.Id.ToString() + (Row.bHidden ? TEXT(" (hidden)") : TEXT(""))))]];
    }
}

void UWarWorldEditWidget::RefreshCatalog()
{
    if (!CatalogRows || !GetWorld()) return;
    CatalogRows->ClearChildren(); CatalogMatches = 0; CatalogTotal = 0;
    const auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); if (!E) return;
    const auto Entries = WarWorldEditCatalog::Build(E->GetHistory().GetBaselineObjects());
    const auto Filtered = WarWorldEditCatalog::Filter(Entries, CatalogSearch);
    CatalogTotal = Entries.Num(); CatalogMatches = Filtered.Num();
    const TWeakObjectPtr<UWarWorldEditWidget> Weak(this);
    for (const auto& Entry : Filtered)
        CatalogRows->AddSlot().AutoHeight().Padding(0, 2)[SNew(SButton).IsFocusable(false)
            .OnClicked_Lambda([Weak, Id = Entry.TemplateId] { if (Weak.IsValid()) Weak->PlaceTemplate(Id); return FReply::Handled(); })
            [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 17)).AutoWrapText(true).Text(FText::FromString(Entry.Label))]];
    if (Filtered.IsEmpty()) CatalogRows->AddSlot().AutoHeight()[SNew(STextBlock)
        .Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).Text(FText::FromString(TEXT("No matching models.")))];
}

void UWarWorldEditWidget::SelectNearest()
{
    CancelPlacement();
    const auto* Pawn = GetOwningPlayerPawn(); const auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    if (!Pawn || !E) return;
    double Best = TNumericLimits<double>::Max();
    for (const auto& Row : E->GetHistory().GetObjects())
    {
        const double Distance = FVector::DistSquared(Row.Transform.GetLocation(), Pawn->GetActorLocation());
        if (Distance < Best) { Best = Distance; Selected = Row.Id; }
    }
}

void UWarWorldEditWidget::PlaceTemplate(const FName TemplateId)
{
    CancelPlacement();
    Selected = NAME_None;
    auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    auto* P = Cast<AWarPlayerController>(GetOwningPlayer());
    UStaticMesh* Mesh = E ? E->GetTemplateMesh(TemplateId) : nullptr;
    auto* Material = PreviewMaterial.Get();
    if (!P || !E || !E->CanUse(P) || !Mesh || !Material)
    { if (P) P->ClientWorldEditResult(TEXT("Required model or preview material unavailable. Nothing placed.")); return; }
    FActorSpawnParameters Params; Params.ObjectFlags |= RF_Transient;
    PreviewActor = GetWorld()->SpawnActor<AStaticMeshActor>(Params);
    if (!PreviewActor) return;
    PreviewActor->SetReplicates(false); PreviewActor->SetActorEnableCollision(false);
    auto* Component = PreviewActor->GetStaticMeshComponent();
    Component->SetMobility(EComponentMobility::Movable); Component->SetStaticMesh(Mesh);
    Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Component->SetCanEverAffectNavigation(false); Component->SetCastShadow(false);
    Component->bAffectDynamicIndirectLighting = false; Component->bAffectDistanceFieldLighting = false;
    auto* Green = UMaterialInstanceDynamic::Create(Material, PreviewActor);
    Green->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.02f, 0.8f, 0.05f, 1.f));
    for (int32 Index = 0; Index < Component->GetNumMaterials(); ++Index) Component->SetMaterial(Index, Green);
    PlacementTemplate = TemplateId;
    FSlateApplication::Get().SetUserFocusToGameViewport(0);
    P->ClientWorldEditResult(TEXT("Move the pointer onto ground or a wall. Green model previews placement; click to place. Cancel placement to select buildings."));
    UpdatePlacement();

}

double UWarWorldEditWidget::GridCentimeters() const
{ constexpr double Steps[] = { 0, 10, 50, 100, 200 }; return Steps[GridIndex]; }

double UWarWorldEditWidget::AngleDegrees() const
{ constexpr double Steps[] = { 15, 45, 90 }; return Steps[AngleIndex]; }

void UWarWorldEditWidget::SnapSelected()
{
    const auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    auto* P = Cast<AWarPlayerController>(GetOwningPlayer());
    const auto* Row = E ? E->GetHistory().Find(Selected) : nullptr;
    if (!P || !Row) return;
    P->ServerEditWorldObject(Selected, WarWorldEditPlacement::SnapTransform(Row->Transform, GridCentimeters(), AngleDegrees()),
        Row->bHidden, E->GetHistory().GetRevision());
}

void UWarWorldEditWidget::SetSelectedComponent(const int32 Field, const double Value)
{
    const auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    auto* P = Cast<AWarPlayerController>(GetOwningPlayer());
    const auto* Row = E ? E->GetHistory().Find(Selected) : nullptr;
    if (!P || !Row) return;
    FTransform Transform = Row->Transform;
    if (WarWorldEditPlacement::SetComponent(Transform, Field, Value))
        P->ServerEditWorldObject(Selected, Transform, Row->bHidden, E->GetHistory().GetRevision());
    else P->ClientWorldEditResult(TEXT("Keep the position within the building's editing bounds, rotation within +/-360 degrees, and scale from 0.05 to 20."));
}

void UWarWorldEditWidget::EditSelected(const FVector Offset, const double Yaw, const double Scale, const bool bToggleHidden)
{
    const auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    auto* P = Cast<AWarPlayerController>(GetOwningPlayer());
    const auto* Row = E ? E->GetHistory().Find(Selected) : nullptr;
    if (!P || !Row) return;
    FTransform Transform = Row->Transform; Transform.AddToTranslation(Offset);
    Transform.SetRotation(FQuat(FVector::UpVector, FMath::DegreesToRadians(Yaw)) * Transform.GetRotation());
    Transform.SetScale3D(Transform.GetScale3D() * Scale);
    P->ServerEditWorldObject(Selected, Transform, bToggleHidden ? !Row->bHidden : Row->bHidden, E->GetHistory().GetRevision());
}

void UWarWorldEditWidget::NativeTick(const FGeometry& Geometry, const float DeltaTime)
{
    Super::NativeTick(Geometry, DeltaTime);
    UpdatePlacement();
    const auto Focus = FSlateApplication::Get().GetUserFocusedWidget(0);
    const bool bTextFocus = Focus && Focus->GetTypeAsString().Contains(TEXT("EditableText"));
    if (bTextFocus != bTextInputLocked)
    {
        if (auto* P = GetOwningPlayer()) P->SetIgnoreMoveInput(bTextFocus);
        bTextInputLocked = bTextFocus;
    }
    if (const auto* P = GetOwningPlayer())
    {
        int32 ViewportWidth = 0, ViewportHeight = 0; P->GetViewportSize(ViewportWidth, ViewportHeight);
        const float DpiScale = FMath::Max(0.1f, UWidgetLayoutLibrary::GetViewportScale(this));
        const float PanelHeight = FMath::Clamp((ViewportHeight - 48.f) / DpiScale, 300.f, 960.f);
        if (!FMath::IsNearlyEqual(PanelHeight, LastPanelHeight))
        { SetDesiredSizeInViewport(FVector2D(560, PanelHeight)); LastPanelHeight = PanelHeight; }
    }
    const auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); if (!E) return;
    if (DisplayedRevision != E->GetHistory().GetRevision()) RefreshRows();
    if (const auto* Actor = Cast<AStaticMeshActor>(E->GetObjectActor(Selected)))
    {
        const auto Bounds = Actor->GetStaticMeshComponent()->Bounds;
        DrawDebugBox(GetWorld(), Bounds.Origin, Bounds.BoxExtent, FColor::Cyan, false, 0, 0, 2);
    }
}

void UWarWorldEditWidget::ReleaseSlateResources(const bool bReleaseChildren)
{ Super::ReleaseSlateResources(bReleaseChildren); Rows.Reset(); CatalogRows.Reset(); RepeatedSection.Reset(); DisplayedRevision = INDEX_NONE; LastPanelHeight = 0; }

bool UWarWorldEditWidget::IsPointerOverPanel() const
{ return GetCachedGeometry().IsUnderLocation(FSlateApplication::Get().GetCursorPos()); }

void UWarWorldEditWidget::UpdatePlacement()
{
    if (!PreviewActor || PlacementTemplate.IsNone()) return;
    auto* P = GetOwningPlayer(); auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    FVector Origin, Direction; FTransform Transform; FString Error;
    bPreviewValid = P && E && !IsPointerOverPanel() && P->DeprojectMousePositionToWorld(Origin, Direction)
        && E->ResolvePlacement(P, PlacementTemplate, Origin, Direction, GridCentimeters(),
            GridCentimeters() > 0 ? AngleDegrees() : 0, Transform, Error);
    PreviewActor->SetActorHiddenInGame(!bPreviewValid);
    if (bPreviewValid) PreviewActor->SetActorTransform(Transform);
}

void UWarWorldEditWidget::CommitPlacement()
{
    UpdatePlacement();
    auto* P = Cast<AWarPlayerController>(GetOwningPlayer());
    auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); FVector Origin, Direction;
    if (!bPreviewValid || !P || !E || !P->DeprojectMousePositionToWorld(Origin, Direction)) return;
    // Resolve the contact again on the authority; never trust a preview transform as an edit.
    P->ServerPlaceWorldObjectAtPointer(PlacementTemplate, Origin, Direction, GridCentimeters(),
        GridCentimeters() > 0 ? AngleDegrees() : 0, E->GetHistory().GetRevision());
}

void UWarWorldEditWidget::CancelPlacement()
{
    if (PreviewActor) PreviewActor->Destroy();
    PreviewActor = nullptr; PlacementTemplate = NAME_None; bPreviewValid = false;
}

void UWarWorldEditWidget::NativeConstruct()
{
    Super::NativeConstruct();
    // Interactive world tools must keep full scene updates while Slate controls have focus.
    if (!bThrottleDisabled) { FSlateThrottleManager::Get().DisableThrottle(true); bThrottleDisabled = true; }
}

void UWarWorldEditWidget::NativeDestruct()
{
    CancelPlacement();
    if (bTextInputLocked) { if (auto* P = GetOwningPlayer()) P->SetIgnoreMoveInput(false); bTextInputLocked = false; }
    if (bThrottleDisabled) { FSlateThrottleManager::Get().DisableThrottle(false); bThrottleDisabled = false; }
    Super::NativeDestruct();
}
