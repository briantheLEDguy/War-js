#include "WarWorldEditWidget.h"
#include "WarWorldEditSubsystem.h"
#include "WarWorldEditPlacement.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "Engine/World.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "GameFramework/Pawn.h"
#include "DrawDebugHelpers.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SSearchBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"
#include "Misc/Paths.h"

TSharedRef<SWidget> UWarWorldEditWidget::RebuildWidget()
{
    const TWeakObjectPtr<UWarWorldEditWidget> Weak(this);
    auto Body = SNew(SVerticalBox);
    Body->AddSlot().AutoHeight()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold", 24)).Text(FText::FromString(TEXT("City Builder")))];
    Body->AddSlot().AutoHeight().Padding(0, 8)[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).Text(FText::FromString(TEXT("Development draft — place and edit buildings")))];
    auto Commands = SNew(SHorizontalBox);
    const auto Button = [](const FString& Label, TFunction<FReply()> Action) -> TSharedRef<SWidget> {
        return SNew(SButton).OnClicked_Lambda(MoveTemp(Action))[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 17)).Text(FText::FromString(Label))];
    };
    Commands->AddSlot().AutoWidth()[Button(TEXT("Close"), [Weak] { if (Weak.IsValid()) if (auto* P = Cast<AWarPlayerController>(Weak->GetOwningPlayer())) P->ToggleWorldEditor(); return FReply::Handled(); })];
    Commands->AddSlot().AutoWidth()[Button(TEXT("Select nearest"), [Weak] { if (Weak.IsValid()) Weak->SelectNearest(); return FReply::Handled(); })];
    for (const bool bRedo : { false, true })
        Commands->AddSlot().AutoWidth()[Button(bRedo ? TEXT("Redo") : TEXT("Undo"), [Weak, bRedo] {
            if (Weak.IsValid()) if (auto* P = Cast<AWarPlayerController>(Weak->GetOwningPlayer()))
                if (auto* E = Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>()) P->ServerWorldEditHistory(bRedo, E->GetHistory().GetRevision());
            return FReply::Handled(); })];
    Body->AddSlot().AutoHeight().Padding(0, 8)[Commands];
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
    auto Catalog = SNew(SVerticalBox);
    TSharedPtr<SHorizontalBox> CatalogRow;
    TSet<FString> Models;
    if (const auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>())
        for (const auto& Row : E->GetHistory().GetBaselineObjects())
        {
            if (Models.Contains(Row.SourceIdentity)) continue;
            Models.Add(Row.SourceIdentity);
            if (Models.Num() % 3 == 1)
            {
                CatalogRow = SNew(SHorizontalBox);
                Catalog->AddSlot().AutoHeight()[CatalogRow.ToSharedRef()];
            }
            FString MeshPath; Row.SourceIdentity.Split(TEXT(":"), &MeshPath, nullptr);
            const FString Label = FPaths::GetBaseFilename(MeshPath).Replace(TEXT("aegis_house_"), TEXT("House "))
                .Replace(TEXT("aegis_rowhouse_"), TEXT("Rowhouse "));
            CatalogRow->AddSlot().FillWidth(1)[Button(Label, [Weak, Id = Row.Id] {
                if (Weak.IsValid()) Weak->PlaceTemplate(Id); return FReply::Handled(); })];
        }
    Body->AddSlot().AutoHeight()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).Text(FText::FromString(TEXT("Place a house in front of your character:")))];
    Body->AddSlot().AutoHeight().Padding(0, 6)[Catalog];
    Body->AddSlot().AutoHeight()[SNew(SSearchBox).HintText(FText::FromString(TEXT("Find a placed building")))
        .OnTextChanged_Lambda([Weak](const FText& Text) { if (Weak.IsValid()) { Weak->Search = Text.ToString(); Weak->RefreshRows(); } })];
    Body->AddSlot().FillHeight(1).Padding(0, 8)[SNew(SScrollBox) + SScrollBox::Slot()[SAssignNew(Rows, SVerticalBox)]];
    Body->AddSlot().AutoHeight()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 17)).AutoWrapText(true).Text_Lambda([Weak] {
        if (!Weak.IsValid()) return FText::GetEmpty();
        auto* E = Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
        const auto* Row = E ? E->GetHistory().Find(Weak->Selected) : nullptr;
        if (!Row) return FText::FromString(TEXT("Select a building to edit."));
        const FVector P = Row->Transform.GetLocation();
        return FText::FromString(FString::Printf(TEXT("%s%s\nX %.1f m   Y %.1f m   Z %.1f m"), *Row->Id.ToString(),
            Row->bHidden ? TEXT(" (hidden)") : TEXT(""), P.X / 100, P.Y / 100, P.Z / 100)); })];
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
    auto Storage = SNew(SHorizontalBox);
    Storage->AddSlot().FillWidth(1)[Button(TEXT("Hide / restore"), [Weak] {
        if (Weak.IsValid()) Weak->EditSelected(FVector::ZeroVector, 0, 1, true); return FReply::Handled(); })];
    for (const bool bLoad : { false, true })
        Storage->AddSlot().FillWidth(1)[Button(bLoad ? TEXT("Load draft") : TEXT("Save draft"), [Weak, bLoad] {
            if (Weak.IsValid()) if (auto* P = Cast<AWarPlayerController>(Weak->GetOwningPlayer()))
                if (auto* E = Weak->GetWorld()->GetSubsystem<UWarWorldEditSubsystem>()) P->ServerWorldEditDraft(bLoad, E->GetHistory().GetRevision());
            return FReply::Handled(); })];
    Body->AddSlot().AutoHeight().Padding(0, 8)[Storage];
    Body->AddSlot().AutoHeight()[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 16)).AutoWrapText(true).Text_Lambda([Weak] {
        const auto* P = Weak.IsValid() ? Cast<AWarPlayerController>(Weak->GetOwningPlayer()) : nullptr;
        return P ? FText::FromString(P->GetWorldEditMessage()) : FText::GetEmpty(); })];
    RefreshRows();
    if (Selected.IsNone()) SelectNearest();
    return SNew(SBox).WidthOverride(560)[SNew(SBorder).Padding(12)
        .BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0.025f, 0.03f, 0.045f, 1.f))[Body]];
}

void UWarWorldEditWidget::RefreshRows()
{
    if (!Rows || !GetWorld()) return;
    Rows->ClearChildren();
    const auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>(); if (!E) return;
    DisplayedRevision = E->GetHistory().GetRevision();
    for (const auto& Row : E->GetHistory().GetObjects())
    {
        if (!Search.IsEmpty() && !Row.Id.ToString().Contains(Search)) continue;
        Rows->AddSlot().AutoHeight().Padding(0, 2)[SNew(SButton)
            .OnClicked_Lambda([Weak = TWeakObjectPtr<UWarWorldEditWidget>(this), Id = Row.Id] { if (Weak.IsValid()) Weak->Selected = Id; return FReply::Handled(); })
            [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 17)).Text(FText::FromString(Row.Id.ToString() + (Row.bHidden ? TEXT(" (hidden)") : TEXT(""))))]];
    }
}

void UWarWorldEditWidget::SelectNearest()
{
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
    auto* P = Cast<AWarPlayerController>(GetOwningPlayer());
    const auto* Pawn = GetOwningPlayerPawn();
    const auto* E = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    if (!P || !Pawn || !E) return;
    const auto* Template = E->GetHistory().GetBaselineObjects().FindByPredicate([TemplateId](const auto& Row) { return Row.Id == TemplateId; });
    if (!Template) return;
    FVector Position = WarWorldEditPlacement::SnapHorizontal(Pawn->GetActorLocation() + Pawn->GetActorForwardVector() * 2000, GridCentimeters());
    FHitResult Hit; FCollisionQueryParams Query; Query.AddIgnoredActor(Pawn);
    if (!GetWorld()->LineTraceSingleByChannel(Hit, Position + FVector(0, 0, 10000), Position - FVector(0, 0, 20000), ECC_Visibility, Query)) return;
    Position.Z = Hit.ImpactPoint.Z;
    FTransform Transform = WarWorldEditPlacement::SnapTransform(Template->Transform, 0, GridCentimeters() > 0 ? AngleDegrees() : 0);
    Transform.SetLocation(Position);
    P->ServerCreateWorldObject(TemplateId, Transform, E->GetHistory().GetRevision());
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
{ Super::ReleaseSlateResources(bReleaseChildren); Rows.Reset(); DisplayedRevision = INDEX_NONE; LastPanelHeight = 0; }
