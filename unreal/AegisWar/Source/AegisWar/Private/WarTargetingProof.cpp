#include "WarInterfaceProof.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "Engine/World.h"
#include "Misc/Paths.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"

void UWarInterfaceProof::TickTargeting(double Now)
{
    auto* PC = Cast<AWarPlayerController>(GetWorld()->GetFirstPlayerController());
    auto* Self = PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    if (!Self) return;
    const auto Check = [this](bool Passed, const TCHAR* Detail) { if (!Passed) Finish(false, Detail); return Passed; };
    FString Run; FGuid Id;
    if (!FParse::Value(FCommandLine::Get(), TEXT("WarTargetingRun="), Run) || !FGuid::Parse(Run, Id))
    { Finish(false, TEXT("Isolated targeting proof ID required")); return; }
    const FString Folder = FPaths::ProjectSavedDir() / TEXT("InterfaceProof") / Id.ToString(EGuidFormats::Digits);
    IFileManager::Get().MakeDirectory(*Folder, true);
    if (Step == 0)
    {
        // Isolated opt-in fixture uses reviewed models; no live server or player state is changed.
        const auto Spawn = [&](bool Enemy)
        {
            auto* Visual = LoadObject<UWarCharacterVisualDefinition>(nullptr, Enemy
                ? TEXT("/Game/Characters/SiegeStaging/Visual_riven_void_magister_m")
                : TEXT("/Game/MigrationProof/Visual_civic_battle_prelate_m"));
            const FVector Forward = FRotationMatrix(FRotator(0, PC->GetLocalCameraState().Yaw, 0)).GetUnitAxis(EAxis::X);
            const FVector Right = FVector::CrossProduct(FVector::UpVector, Forward);
            FActorSpawnParameters Params; Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            auto* Pawn = GetWorld()->SpawnActor<AWarCharacter>(Self->GetActorLocation() + Forward * 450 + Right * (Enemy ? 120 : -120),
                (-Forward).Rotation(), Params);
            auto* State = GetWorld()->SpawnActor<AWarPlayerState>(); Pawn->SetPlayerState(State);
            State->SetDevelopmentRealm(Enemy ? EWarRealm::Riftbound : EWarRealm::Aegis);
            State->SetCurrentZoneTrusted(PC->GetPlayerState<AWarPlayerState>()->GetCurrentZone());
            State->SetPlayerName(Enemy ? TEXT("Enemy reticle") : TEXT("Friendly reticle"));
            FString Error;
            if (!Pawn->SetVisualDefinition(Visual, Error)) { Finish(false, TEXT("Reticle fixture model failed to load")); return static_cast<AActor*>(nullptr); }
            State->InitializeForPawn(Pawn);
            return static_cast<AActor*>(Pawn);
        };
        FriendlyTarget = Spawn(false); EnemyTarget = Spawn(true);
        PC->GetLocalCameraState().Pitch = -12;
        if (!Check(PC->bShowMouseCursor, TEXT("Gameplay cursor unavailable"))) return;
    }
    else if (Step == 1)
    {
        PC->TargetNearestEnemy();
        if (!Check(PC->GetCombatTarget() == EnemyTarget.Get(), TEXT("Nearest enemy selection failed"))) return;
    }
    else if (Step == 2) FScreenshotRequest::RequestScreenshot(Folder / TEXT("target-enemy.png"), true, false);
    else if (Step == 3)
    {
        FVector2D Point;
        if (!Check(FriendlyTarget.IsValid() && PC->ProjectWorldLocationToScreen(FriendlyTarget->GetActorLocation(), Point), TEXT("Friendly target not projected"))) return;
        PC->SetMouseLocation(FMath::RoundToInt(Point.X), FMath::RoundToInt(Point.Y));
    }
    else if (Step == 4)
    {
        PC->SelectCombatTargetUnderCursor();
        if (!Check(PC->GetCombatTarget() == FriendlyTarget.Get(), TEXT("Pointer did not select the friendly target"))) return;
    }
    else if (Step == 5) FScreenshotRequest::RequestScreenshot(Folder / TEXT("target-friendly.png"), true, false);
    else if (Step == 6)
    {
        PC->CycleCombatTarget();
        if (!Check(PC->GetCombatTarget() == EnemyTarget.Get(), TEXT("Enemy cycle retained an ally"))) return;
        PC->ToggleInventory(); PC->ToggleInventory(); PC->ToggleQuestLog(); PC->ToggleQuestLog();
        PC->ShowInterface(TEXT("Menu")); PC->CloseInterface();
        if (!Check(PC->bShowMouseCursor && !PC->IsMoveInputIgnored() && !PC->IsLookInputIgnored(), TEXT("Panel closure lost gameplay cursor/input"))) return;
    }
    else if (Step == 7) { Finish(true, TEXT("Nearest enemy, ally pointer selection, enemy cycling and cursor restoration passed; reticle captures require visual review.")); return; }
    ++Step; NextStep = Now + 1;
}
