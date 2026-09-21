#include "WarQuestHud.h"
#include "WarQuestMarkerRules.h"
#include "WarQuestNpc.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "WarContentSubsystem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"

void AWarQuestHud::DrawHUD()
{
    Super::DrawHUD();
    auto* Controller = GetOwningPlayerController();
    const auto* State = Controller ? Controller->GetPlayerState<AWarPlayerState>() : nullptr;
    const auto* Character = Controller ? Cast<AWarCharacter>(Controller->GetPawn()) : nullptr;
    const auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    if (!Canvas || !GEngine || !Controller || !Controller->IsLocalController() || !State || !Character
        || !Character->IsVisualReady() || !Content || !Content->IsContentReady()) return;
    const FName Realm = State->GetRealm() == EWarRealm::Aegis ? FName(TEXT("aegis"))
        : State->GetRealm() == EWarRealm::Riftbound ? FName(TEXT("riftbound")) : NAME_None;
    const auto& Snapshot = State->GetInventory();
    for (TActorIterator<AWarQuestNpc> It(GetWorld()); It; ++It)
    {
        // Admission validates identities/imports; drawing must not synchronously reload all animations every frame.
        if (It->IsHidden() || It->IsActorBeingDestroyed() || !It->GetSkeletalMeshComponent()->IsVisible()
            || !It->GetSkeletalMeshComponent()->GetSkeletalMeshAsset()) continue;
        const auto Marker = WarQuestMarkers::Resolve(Content->GetQuestsForNpc(It->ZoneId, It->NpcId),
            Snapshot.Quests, Realm, It->ZoneId, It->NpcId, Snapshot.CharacterProgression.Level);
        if (Marker == EWarQuestMarker::None) continue;
        FVector2D Position;
        if (!Controller->ProjectWorldLocationToScreen(It->GetActorLocation() + FVector(0, 0, 260), Position, true)
            || !FMath::IsFinite(Position.X) || !FMath::IsFinite(Position.Y)
            || Position.X < 0 || Position.Y < 0 || Position.X >= Canvas->SizeX || Position.Y >= Canvas->SizeY) continue;
        const FString Label = Marker == EWarQuestMarker::TurnIn ? TEXT("?") : TEXT("!");
        UFont* Font = GEngine->GetLargeFont();
        float Width, Height;
        GetTextSize(Label, Width, Height, Font);
        if (Height <= 0.f) continue;
        const float Scale = 26.f / Height;
        const float Bob = 2.f - 2.f * FMath::Cos(GetWorld()->GetTimeSeconds() * PI / 1.2f);
        const float X = Position.X - Width * Scale * 0.5f, Y = Position.Y - Height * Scale - Bob;
        DrawText(Label, FLinearColor::Black, X + 2, Y + 2, Font, Scale);
        DrawText(Label, Marker == EWarQuestMarker::TurnIn ? FLinearColor(1.f, 0.8f, 0.2f) : FLinearColor(1.f, 0.93f, 0.4f), X, Y, Font, Scale);
    }
}
