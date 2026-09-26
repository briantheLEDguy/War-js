#include "WarInterfaceProof.h"
#include "WarWorldEditWidget.h"
#include "WarWorldEditSubsystem.h"
#include "WarWorldEditCatalog.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UObject/UObjectIterator.h"
#include "UnrealClient.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Application/ThrottleManager.h"

namespace
{
    bool ClickBuilderButton(const TSharedRef<SWidget>& Widget, const FString& Label)
    {
        if (Widget->GetTypeAsString() == TEXT("SButton"))
        {
            const auto Button = StaticCastSharedRef<SButton>(Widget);
            const auto Content = Button->GetContent();
            if (Content->GetTypeAsString() == TEXT("STextBlock")
                && StaticCastSharedRef<STextBlock>(Content)->GetText().ToString() == Label)
            { Button->SimulateClick(); return true; }
        }
        auto* Children = Widget->GetChildren();
        for (int32 Index = 0; Children && Index < Children->Num(); ++Index)
            if (ClickBuilderButton(Children->GetChildAt(Index), Label)) return true;
        return false;
    }
}

void UWarInterfaceProof::TickWorldBuilder(double Now)
{
    auto* PC = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Pawn = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    if (!PC || !Pawn || !Editor) return;
    FString Error;
    const FString Folder = FPaths::GetPath(Editor->GetDraftLocation());
    const auto Check = [this, &Folder](bool Passed, const FString& Detail) {
        if (!Passed) { FFileHelper::SaveStringToFile(Detail, *(Folder / TEXT("failure.txt"))); Finish(false, Detail); }
        return Passed;
    };
    if (FParse::Param(FCommandLine::Get(), TEXT("WarBuilderReload")))
    {
        // World subsystems can tick before the controller on the first ready frame.
        if (Step == 0) { ++Step; NextStep = Now + 2; return; }
        const auto* Created = Editor->GetHistory().GetObjects().FindByPredicate([](const auto& Row) { return !Row.TemplateId.IsNone(); });
        if (!Check(Created && Editor->GetObjectActor(Created->Id)
            && Editor->GetObjectActor(Created->Id)->GetActorTransform().Equals(Created->Transform),
            TEXT("Published object was not restored before opening the UI: ") + PC->GetWorldEditMessage())) return;
        FFileHelper::SaveStringToFile(TEXT("{\"passed\":true,\"restoredPublication\":true}"), *(Folder / TEXT("reload-report.json")));
        Finish(true, TEXT("Published object restored in a fresh process")); return;
    }
    if (!Check(Editor->Open(PC, Error), TEXT("Builder could not initialize: ") + Error)) return;
    UWarWorldEditWidget* Widget = nullptr;
    for (TObjectIterator<UWarWorldEditWidget> It; It; ++It)
        if (It->GetOwningPlayer() == PC && It->IsInViewport()) { Widget = *It; break; }
    if (Step == 0)
    {
        if (Now < 20) { NextStep = 20; return; }
        IFileManager::Get().MakeDirectory(*Folder, true);
        BuilderStart = Pawn->GetActorLocation(); BuilderObjectCount = Editor->GetHistory().GetObjects().Num();
        FScreenshotRequest::RequestScreenshot(Folder / TEXT("before.png"), true, false);
    }
    else if (Step == 1)
    {
        PC->ToggleWorldEditor();
        if (!Check(PC->IsWorldEditorOpen() && !PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored(), TEXT("Builder blocked gameplay input"))) return;
    }
    else if (Step == 2)
    {
        if (!Check(Widget != nullptr, TEXT("Builder widget missing"))) return;
        auto Request = FSlateThrottleManager::Get().EnterResponsiveMode();
        const bool Unthrottled = FSlateThrottleManager::Get().IsAllowingExpensiveTasks();
        FSlateThrottleManager::Get().LeaveResponsiveMode(Request);
        if (!Check(Unthrottled, TEXT("Builder allowed Slate to throttle scene rendering"))) return;
        FScreenshotRequest::RequestScreenshot(Folder / TEXT("builder.png"), true, false);
    }
    else if (Step == 3)
    {
        if (!Check(Widget != nullptr, TEXT("Builder closed unexpectedly"))) return;
        double Best = TNumericLimits<double>::Max();
        const auto Catalog = WarWorldEditCatalog::Build(Editor->GetHistory().GetBaselineObjects());
        FString Label;
        for (const auto& Entry : Catalog)
            if (const auto* Mesh = Editor->GetTemplateMesh(Entry.TemplateId); Mesh && Mesh->GetBoundingBox().GetExtent().Size() < Best)
            { Best = Mesh->GetBoundingBox().GetExtent().Size(); BuilderTemplate = Entry.TemplateId; Label = Entry.Label; }
        if (!Check(!Label.IsEmpty() && ClickBuilderButton(Widget->TakeWidget(), Label), TEXT("Catalog selection unavailable"))) return;
        if (!Check(Widget->PreviewActor && Widget->HasPlacement()
            && !Widget->PreviewActor->GetActorEnableCollision() && !Widget->PreviewActor->GetIsReplicated()
            && Editor->GetHistory().GetObjects().Num() == BuilderObjectCount, TEXT("Selection did not create an isolated model preview"))) return;
        int32 Width, Height; PC->GetViewportSize(Width, Height);
        bool Found = false;
        for (int32 Y = Height * 3 / 4; Y < Height * 9 / 10 && !Found; Y += 15)
            for (int32 X = Width * 2 / 3; X < Width * 9 / 10 && !Found; X += 15)
            {
                FVector Origin, Direction; FTransform Placement;
                if (PC->DeprojectScreenPositionToWorld(X, Y, Origin, Direction)
                    && Editor->ResolvePlacement(PC, BuilderTemplate, Origin, Direction, 0, 0, Placement, Error))
                { PC->SetMouseLocation(X, Y); Found = true; }
            }
        if (!Check(Found, TEXT("No visible support surface for preview"))) return;
    }
    else if (Step == 4)
    {
        if (!Check(Widget && Widget->bPreviewValid && !Widget->PreviewActor->IsHidden(), TEXT("Green pointer preview is not visible"))) return;
        FScreenshotRequest::RequestScreenshot(Folder / TEXT("preview.png"), true, false);
        Pawn->ToggleAutoRun();
    }
    else if (Step == 5)
    {
        Pawn->ToggleAutoRun(); Pawn->GetCharacterMovement()->StopMovementImmediately();
        if (!Check(FVector::Dist2D(BuilderStart, Pawn->GetActorLocation()) > 20, TEXT("Character failed to move while builder was open"))) return;
        if (!Check(Widget != nullptr, TEXT("Movement closed builder"))) return;
        TWeakObjectPtr<AActor> Preview = Widget->PreviewActor;
        Widget->CancelPlacement();
        if (!Check(!Preview.IsValid() && !Widget->HasPlacement(), TEXT("Cancel retained preview"))) return;
        Widget->PlaceTemplate(BuilderTemplate);
    }
    else if (Step == 6)
    {
        PC->PickWorldEditorObject();
        if (!Check(Widget && !Widget->HasPlacement() && Editor->GetHistory().GetObjects().Num() == BuilderObjectCount + 1,
            TEXT("Pointer click failed to commit preview"))) return;
        if (!Check(!Editor->Publish(PC, Editor->GetHistory().GetRevision() - 1, Error), TEXT("Stale publication was accepted"))) return;
        if (!Check(ClickBuilderButton(Widget->TakeWidget(), TEXT("Publish draft to local game"))
            && PC->GetWorldEditMessage().StartsWith(TEXT("Published to this local game.")), TEXT("Publish button failed: ") + PC->GetWorldEditMessage())) return;
        PC->ToggleWorldEditor();
        if (!Check(!PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored() && !PC->bShowMouseCursor
            && !Widget->bThrottleDisabled, TEXT("Builder close leaked input or rendering state"))) return;
    }
    else if (Step == 7)
    {
        FFileHelper::SaveStringToFile(TEXT("{\"passed\":true,\"movement\":true,\"preview\":true,\"publication\":true,\"sharedPublication\":false}"), *(Folder / TEXT("report.json")));
        Finish(true, TEXT("Builder rendering state, movement, catalog preview, cancellation, placement and publication passed")); return;
    }
    ++Step; NextStep = Now + 2;
}
