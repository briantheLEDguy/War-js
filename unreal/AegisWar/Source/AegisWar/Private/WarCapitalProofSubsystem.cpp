#include "WarCapitalProofSubsystem.h"
#include "WarWorldEditSubsystem.h"
#include "WarPlayerController.h"
#include "WarCharacter.h"
#include "Components/BoxComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "UnrealClient.h"
#include "TimerManager.h"

bool UWarCapitalProofSubsystem::ShouldCreateSubsystem(UObject* Outer) const
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return Super::ShouldCreateSubsystem(Outer) && FParse::Param(FCommandLine::Get(), TEXT("WarCapitalProof"))
        && FParse::Param(FCommandLine::Get(), TEXT("WarDevelopmentGM"));
#endif
}
bool UWarCapitalProofSubsystem::DoesSupportWorldType(const EWorldType::Type Type) const { return Type == EWorldType::Game; }
TStatId UWarCapitalProofSubsystem::GetStatId() const { RETURN_QUICK_DECLARE_CYCLE_STAT(UWarCapitalProofSubsystem, STATGROUP_Tickables); }

void UWarCapitalProofSubsystem::Finish(const bool bPassed, const FString& Detail)
{
    bFinished = true;
    FString Run; FParse::Value(FCommandLine::Get(), TEXT("WarProofRun="), Run);
    if (Run.IsEmpty() || Run.Len() > 64 || Run.Contains(TEXT("..")) || Run.Contains(TEXT("/")) || Run.Contains(TEXT("\\")))
    { FPlatformMisc::RequestExitWithStatus(false, 1); return; }
    const FString Directory = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("CapitalProof"), Run);
    IFileManager::Get().MakeDirectory(*Directory, true);
    const auto Report = MakeShared<FJsonObject>();
    Report->SetNumberField(TEXT("schemaVersion"), 1); Report->SetBoolField(TEXT("passed"), bPassed);
    Report->SetStringField(TEXT("detail"), Detail); Report->SetBoolField(TEXT("fullCapitalAcceptance"), false);
    Report->SetBoolField(TEXT("sharedGmAuthorization"), false);
    Report->SetBoolField(TEXT("constructionReload"), FParse::Param(FCommandLine::Get(), TEXT("WarCapitalReloadProof")));
    if (const auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>())
    {
        Report->SetNumberField(TEXT("editableObjects"), Editor->GetHistory().GetObjects().Num());
        Report->SetNumberField(TEXT("retainedBaselineAdditions"), Editor->GetHistory().GetLoadedBaselineAdditions());
        Report->SetStringField(TEXT("isolatedDraft"), Editor->GetDraftLocation());
    }
    FString Json; FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json, *FPaths::Combine(Directory, TEXT("report.json")));
    if (bPassed && FParse::Param(FCommandLine::Get(), TEXT("WarProofScreenshot")))
    {
        const FString Image = FPaths::Combine(Directory, TEXT("builder.png"));
        FTimerHandle Capture;
        GetWorld()->GetTimerManager().SetTimer(Capture, [Image] { FScreenshotRequest::RequestScreenshot(Image, true, false); }, 0.5f, false);
    }
    FTimerHandle Exit;
    GetWorld()->GetTimerManager().SetTimer(Exit, [bPassed] { FPlatformMisc::RequestExitWithStatus(false, bPassed ? 0 : 1); }, 2.f, false);
}

void UWarCapitalProofSubsystem::Tick(const float DeltaTime)
{
    if (bFinished || !GetWorld()->HasBegunPlay()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    if (StartedAt < 0) StartedAt = Now;
    auto* Player = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Character = Player ? Cast<AWarCharacter>(Player->GetPawn()) : nullptr;
    auto* Editor = GetWorld()->GetSubsystem<UWarWorldEditSubsystem>();
    if (!Character || !Editor || !Character->GetCharacterMovement()->IsMovingOnGround())
    {
        if (Now - StartedAt > 30) Finish(false, TEXT("Capital character failed to reach authored ground."));
        return;
    }
    if (Stage == 0)
    {
        StartPosition = Character->GetActorLocation(); Character->ToggleAutoRun(); Stage = 1; return;
    }
    if (Stage == 1)
    {
        if (FVector::Dist2D(StartPosition, Character->GetActorLocation()) < 100)
        { if (Now - StartedAt > 30) Finish(false, TEXT("Capital movement failed.")); return; }
        Character->ToggleAutoRun(); Character->GetCharacterMovement()->StopMovementImmediately(); Stage = 2;
    }
    FString Error;
    const auto Check = [this](const bool Passed, const FString& Detail) { if (!Passed) Finish(false, Detail); return Passed; };
    if (!Check(!Editor->CanUse(nullptr), TEXT("Unauthenticated workbench access allowed."))) return;
    Player->ToggleWorldEditor();
    if (!Check(Editor->GetHistory().GetObjects().Num() == 109 && Player->IsMoveInputIgnored() && Player->IsLookInputIgnored(),
        FString::Printf(TEXT("GM panel did not open: %s; map=%s net=%d"), *Player->GetWorldEditMessage(),
            *GetWorld()->GetMapName(), static_cast<int32>(GetWorld()->GetNetMode())))) return;
    const auto CheckCreated = [&](const FName CreatedId) {
        const auto* Row = Editor->GetHistory().Find(CreatedId);
        auto* CreatedActor = Cast<AStaticMeshActor>(Editor->GetObjectActor(CreatedId));
        auto* TemplateActor = Row ? Cast<AStaticMeshActor>(Editor->GetObjectActor(Row->TemplateId)) : nullptr;
        if (!Check(Row && CreatedActor && TemplateActor && !CreatedActor->IsHidden()
            && CreatedActor->GetStaticMeshComponent()->GetStaticMesh() == TemplateActor->GetStaticMeshComponent()->GetStaticMesh()
            && CreatedActor->GetActorTransform().Equals(Row->Transform, 0.01), TEXT("Created building lost its authored model or transform."))) return false;
        TArray<UBoxComponent*> CreatedBoxes; CreatedActor->GetComponents(CreatedBoxes);
        if (!Check(CreatedBoxes.Num() == 1, TEXT("Created building lost authored collision."))) return false;
        const auto* Box = CreatedBoxes[0]; const FVector Center = Box->GetComponentLocation(), Extent = Box->GetScaledBoxExtent();
        FHitResult Hit;
        return Check(GetWorld()->LineTraceSingleByChannel(Hit, Center + FVector(0, 0, Extent.Z + 25), Center, ECC_Visibility)
            && Hit.GetActor() == CreatedActor && FMath::Abs(Hit.ImpactPoint.Z - Center.Z - Extent.Z) < 0.2,
            TEXT("Created building has no blocking collision."));
    };
    if (FParse::Param(FCommandLine::Get(), TEXT("WarCapitalReloadProof")))
    {
        Player->ServerWorldEditDraft(true, 0);
        if (!Check(Editor->GetHistory().GetObjects().Num() == 110, TEXT("Fresh process did not restore construction draft."))) return;
        if (!Check(Editor->GetHistory().GetLoadedBaselineAdditions() == 1, TEXT("Fresh process did not retain the newly authored object."))) return;
        const auto* Created = Editor->GetHistory().GetObjects().FindByPredicate([](const auto& Row) { return !Row.TemplateId.IsNone(); });
        if (!Check(Created != nullptr, TEXT("Fresh draft lost created identity.")) || !CheckCreated(Created->Id)) return;
        Finish(true, TEXT("Fresh process restored the constructed complex building, transform and blocking collision.")); return;
    }
    const FName Id(TEXT("aegis_city_house_0"));
    const auto* Initial = Editor->GetHistory().Find(Id);
    if (!Check(Initial != nullptr, TEXT("Missing edited house."))) return;
    const FTransform Original = Initial->Transform;
    FTransform Moved = Original; Moved.AddToTranslation(FVector(1200, 0, 0));
    Moved.SetRotation(FQuat(FVector::UpVector, FMath::DegreesToRadians(30.0)) * Moved.GetRotation());
    Moved.SetScale3D(Moved.GetScale3D() * 1.2);
    AActor* Actor = Editor->GetObjectActor(Id);
    TArray<UBoxComponent*> Boxes;
    if (Actor) Actor->GetComponents(Boxes);
    if (!Check(Boxes.Num() == 1, TEXT("Unexpected authored house collision."))) return;
    const FTransform ExpectedBox = Boxes[0]->GetRelativeTransform() * Moved;
    Player->ServerEditWorldObject(Id, Moved, false, 0);
    if (!Check(Actor && Actor->GetActorTransform().Equals(Moved, 0.01) && Editor->GetHistory().GetRevision() == 1,
        TEXT("Server GM transform was not applied."))) return;
    Player->ServerEditWorldObject(Id, Original, false, 0);
    if (!Check(Editor->GetHistory().GetRevision() == 1, TEXT("Stale GM edit accepted."))) return;
    const auto* Box = Boxes[0];
    if (!Check(Box->GetComponentTransform().Equals(ExpectedBox, 0.01), TEXT("Collision detached from edited model transform."))) return;
    const FVector Center = Box->GetComponentLocation(), Extent = Box->GetScaledBoxExtent();
    FHitResult Hit;
    const bool bHit = GetWorld()->LineTraceSingleByChannel(Hit, Center + FVector(0, 0, Extent.Z + 25), Center, ECC_Visibility);
    if (!Check(bHit && Hit.GetActor() == Actor && FMath::Abs(Hit.ImpactPoint.Z - Center.Z - Extent.Z) < 0.2,
        TEXT("GM transform did not preserve native collision."))) return;
    Player->ServerEditWorldObject(Id, Moved, true, 1);
    if (!Check(Actor->IsHidden() && !Actor->GetActorEnableCollision(), TEXT("Hidden GM object retained collision."))) return;
    Player->ServerWorldEditHistory(false, 2);
    if (!Check(!Actor->IsHidden() && Actor->GetActorEnableCollision(), TEXT("GM undo did not restore collision."))) return;
    Player->ServerWorldEditHistory(true, 3);
    Player->ServerWorldEditHistory(false, 4);
    Player->ServerWorldEditDraft(false, 5);
    FString Saved;
    if (!Check(FFileHelper::LoadFileToString(Saved, *Editor->GetDraftLocation()), TEXT("GM draft was not saved."))) return;
    Player->ServerEditWorldObject(Id, Original, false, 5);
    Player->ServerWorldEditDraft(true, 6);
    if (!Check(Editor->GetHistory().GetRevision() == 7 && Actor->GetActorTransform().Equals(Moved, 0.01), TEXT("GM draft reload failed."))) return;
    FFileHelper::SaveStringToFile(TEXT("{}"), *Editor->GetDraftLocation());
    Player->ServerWorldEditDraft(false, 7);
    FString External;
    FFileHelper::LoadFileToString(External, *Editor->GetDraftLocation());
    if (!Check(External == TEXT("{}"), TEXT("GM save overwrote an external draft change."))) return;
    Player->ServerWorldEditDraft(true, 7);
    if (!Check(Editor->GetHistory().GetRevision() == 7, TEXT("Malformed draft modified live world."))) return;
    FFileHelper::SaveStringToFile(Saved, *Editor->GetDraftLocation());
    Player->ServerWorldEditHistory(false, 7);
    if (!Check(Actor->GetActorTransform().Equals(Original, 0.01), TEXT("Loaded draft cannot be undone."))) return;
    FTransform Placed = Original; Placed.AddToTranslation(FVector(0, 0, 5000));
    const int32 BeforeCreate = Editor->GetHistory().GetRevision();
    Player->ServerCreateWorldObject(TEXT("unregistered"), Placed, BeforeCreate);
    if (!Check(Editor->GetHistory().GetRevision() == BeforeCreate, TEXT("Unknown building template accepted."))) return;
    Player->ServerCreateWorldObject(Id, Placed, BeforeCreate - 1);
    if (!Check(Editor->GetHistory().GetRevision() == BeforeCreate, TEXT("Stale building creation accepted."))) return;
    Player->ServerCreateWorldObject(Id, Placed, BeforeCreate);
    const auto* Created = Editor->GetHistory().GetObjects().FindByPredicate([](const auto& Row) { return !Row.TemplateId.IsNone(); });
    if (!Check(Created != nullptr && Editor->GetHistory().GetObjects().Num() == 110, TEXT("GM construction failed."))) return;
    const FName CreatedId = Created->Id;
    if (!CheckCreated(CreatedId)) return;
    Player->ServerWorldEditHistory(false, Editor->GetHistory().GetRevision());
    if (!Check(!Editor->GetObjectActor(CreatedId) && !Editor->GetHistory().Find(CreatedId), TEXT("Undo retained a created actor."))) return;
    Player->ServerWorldEditHistory(true, Editor->GetHistory().GetRevision());
    if (!CheckCreated(CreatedId)) return;
    Player->ServerWorldEditDraft(false, Editor->GetHistory().GetRevision());
    if (!Check(FFileHelper::LoadFileToString(Saved, *Editor->GetDraftLocation()) && Saved.Contains(CreatedId.ToString()), TEXT("Construction was not saved."))) return;
    // Model a draft written before one baseline building was imported. The
    // separate reload process must retain that new building and the GM creation.
    TSharedPtr<FJsonObject> OlderDraft, OlderBaseline;
    if (!Check(FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Saved), OlderDraft)
        && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(OlderDraft->GetStringField(TEXT("baseline"))), OlderBaseline),
        TEXT("Could not prepare additive import fixture."))) return;
    auto BaseRows = OlderBaseline->GetArrayField(TEXT("objects"));
    const FString AddedId = BaseRows.Last()->AsObject()->GetStringField(TEXT("id"));
    BaseRows.Pop(); OlderBaseline->SetArrayField(TEXT("objects"), BaseRows);
    FString OlderBaseText; FJsonSerializer::Serialize(OlderBaseline.ToSharedRef(), TJsonWriterFactory<>::Create(&OlderBaseText));
    OlderDraft->SetStringField(TEXT("baseline"), OlderBaseText);
    auto DraftRows = OlderDraft->GetArrayField(TEXT("objects"));
    DraftRows.RemoveAll([&](const auto& Value) { return Value->AsObject()->GetStringField(TEXT("id")) == AddedId; });
    OlderDraft->SetArrayField(TEXT("objects"), DraftRows);
    FString OlderText; FJsonSerializer::Serialize(OlderDraft.ToSharedRef(), TJsonWriterFactory<>::Create(&OlderText));
    if (!Check(FFileHelper::SaveStringToFile(OlderText, *Editor->GetDraftLocation()), TEXT("Could not write earlier-baseline draft."))) return;
    Player->ServerWorldEditHistory(false, Editor->GetHistory().GetRevision());
    Player->ServerWorldEditDraft(true, Editor->GetHistory().GetRevision());
    if (!CheckCreated(CreatedId)) return;
    if (!Check(Editor->GetHistory().GetLoadedBaselineAdditions() == 1 && Editor->GetObjectActor(FName(*AddedId)) != nullptr,
        TEXT("Older draft removed newly imported capital content."))) return;
    Player->ServerWorldEditHistory(false, Editor->GetHistory().GetRevision());
    Player->ToggleInventory(); Player->ToggleWorldEditor(); Player->ToggleQuestLog(); Player->ToggleWorldEditor(); Player->ToggleWorldEditor();
    if (!Check(!Player->IsMoveInputIgnored() && !Player->IsLookInputIgnored() && !Player->bShowMouseCursor,
        TEXT("GM panel transitions left movement/camera blocked."))) return;
    Player->ToggleWorldEditor();
    Finish(true, TEXT("Capital movement, GM transforms/collision, construction, revisions, undo/redo, draft save/load and modal controls passed."));
}
