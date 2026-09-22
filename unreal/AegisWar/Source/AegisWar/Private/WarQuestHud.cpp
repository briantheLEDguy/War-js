#include "WarQuestHud.h"
#include "WarPlayerController.h"
#include "WarQuestMarkerRules.h"
#include "WarQuestNpc.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "WarEnemy.h"
#include "WarAttributeSet.h"
#include "WarCityNpc.h"
#include "WarInterfaceRules.h"
#include "WarContentSubsystem.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Canvas.h"
#include "ImageUtils.h"
#include "Engine/Texture2D.h"
#include "Misc/Paths.h"
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
    // Canvas HUD reads replicated state; it never invents local combat or quest progress.
    const float HudScale = FMath::Clamp(Canvas->SizeY / 900.f, 0.65f, 1.5f);
    if (!bArtworkLoaded)
    {
        bArtworkLoaded = true;
        VitalsArtwork = FImageUtils::ImportFileAsTexture2D(FPaths::Combine(FPaths::ProjectContentDir(),TEXT("UI/healthbar.png")));
        MinimapArtwork = FImageUtils::ImportFileAsTexture2D(FPaths::Combine(FPaths::ProjectContentDir(),TEXT("UI/minimap.png")));
    }
    const float Left = 16 * HudScale, Top = 20 * HudScale, FrameWidth = 440 * HudScale, FrameHeight = FrameWidth/3;
    const float FrameTop = Top + 18 * HudScale, BarLeft = Left + FrameWidth*.247f, HudWidth = FrameWidth*.658f;
    if (VitalsArtwork) DrawTexture(VitalsArtwork,Left,FrameTop,FrameWidth,FrameHeight,0,0,1,1);
    else DrawRect(FLinearColor(.015f,.022f,.035f,.9f),Left,FrameTop,FrameWidth,FrameHeight);
    UFont* HudFont = GEngine->GetSmallFont();
    const auto& Progress = State->GetInventory().CharacterProgression;
    DrawText(FString::Printf(TEXT("%s  |  Level %d"), *State->GetPlayerName(), Progress.Level), FLinearColor::White, Left, Top, HudFont, HudScale);
    const auto Bar = [&](const FString& Label, float Value, float Maximum, float Y, FLinearColor Colour) {
        const float Height = FrameHeight*.1f;
        DrawRect(Colour, BarLeft, Y, HudWidth * (Maximum > 0 ? FMath::Clamp(Value / Maximum, 0.f, 1.f) : 0.f), Height);
        DrawText(FString::Printf(TEXT("%s  %.0f / %.0f"), *Label, Value, Maximum), FLinearColor::White, BarLeft + 5 * HudScale, Y, HudFont, HudScale*.85f);
    };
    if (const auto* Attributes = State->GetAttributes())
    {
        Bar(TEXT("Health"), Attributes->GetHealth(), Attributes->GetMaxHealth(), FrameTop + FrameHeight*.328f, FLinearColor(.5f,.09f,.1f,.85f));
        Bar(TEXT("Mana"), Attributes->GetMana(), Attributes->GetMaxMana(), FrameTop + FrameHeight*.482f, FLinearColor(.06f,.2f,.55f,.85f));
    }
    Bar(TEXT("XP"), Progress.Xp, WarProgression::XpForLevel(Progress.Level), FrameTop + FrameHeight*.635f, FLinearColor(.45f,.32f,.08f,.8f));
    DrawText(FString::Printf(TEXT("Gold %lld"), Progress.Gold), FLinearColor(.9f,.78f,.5f), BarLeft,FrameTop+FrameHeight*.79f,HudFont,HudScale*.8f);
    const float Footer = Canvas->SizeY - 66 * HudScale;
    if (const auto* PC = Cast<AWarPlayerController>(Controller); PC && !PC->GetZoneTravelStatus().IsEmpty())
        DrawText(PC->GetZoneTravelStatus(), FLinearColor(0.65f, 0.85f, 1.f), Left, Footer - 32 * HudScale, HudFont, HudScale);
    DrawRect(FLinearColor(0.015f, 0.022f, 0.035f, 0.9f), 0, Footer - 8, Canvas->SizeX, 74 * HudScale);
    const auto KeyLabel=[Controller](const TCHAR* Action) { const auto* PC=Cast<AWarPlayerController>(Controller); return PC ? PC->GetControlKey(FName(Action)).GetDisplayName().ToString() : FString(TEXT("?")); };
    DrawText(FString::Printf(TEXT("[Esc] Menu   [%s] Map   [%s] Character   [%s] Inventory   [%s] Quests   [F1] Guide"), *KeyLabel(TEXT("Map")), *KeyLabel(TEXT("Character")), *KeyLabel(TEXT("Inventory")), *KeyLabel(TEXT("Quests"))),
        FLinearColor(0.92f, 0.84f, 0.64f), Left, Footer, HudFont, HudScale);
    DrawText(Character->IsDead() ? TEXT("Defeated - waiting for respawn") : FString::Printf(TEXT("[%s] Interact   |   [%s] Target   |   [%s] Action cursor   |   [Esc] UI Settings"),*KeyLabel(TEXT("Interact")),*KeyLabel(TEXT("CycleTarget")),*KeyLabel(TEXT("ActionCursor"))),
        FLinearColor::White, Left, Footer + 25 * HudScale, HudFont, HudScale);
    const float MapFrame = 220 * HudScale, MapSize = MapFrame*.70f;
    const FVector2D MapFrameOrigin(Canvas->SizeX-MapFrame-12*HudScale,12*HudScale);
    const FVector2D MapOrigin = MapFrameOrigin + FVector2D(MapFrame*.15f,MapFrame*.15f);
    if (MinimapArtwork) DrawTexture(MinimapArtwork,MapFrameOrigin.X,MapFrameOrigin.Y,MapFrame,MapFrame,0,0,1,1);
    else DrawRect(FLinearColor(.015f,.025f,.035f,.9f),MapOrigin.X,MapOrigin.Y,MapSize,MapSize);
    DrawText(TEXT("N   |   Local radar [")+KeyLabel(TEXT("Map"))+TEXT("]"), FLinearColor::White, MapOrigin.X,MapFrameOrigin.Y+MapFrame,HudFont,HudScale*.85f);
    for (TActorIterator<AWarCityNpc> It(GetWorld()); It; ++It)
    {
        if (It->IsHidden() || It->GetService().IsNone()) continue;
        const auto Point = WarInterface::MapPoint(It->GetActorLocation(), Character->GetActorLocation(), 10000, FVector2D(MapSize, MapSize));
        if (Point.X < 4 || Point.Y < 4 || Point.X > MapSize - 4 || Point.Y > MapSize - 4) continue;
        DrawRect(FLinearColor(0.35f, 0.8f, 1.f), MapOrigin.X + Point.X - 2, MapOrigin.Y + Point.Y - 2, 4 * HudScale, 4 * HudScale);
    }
    DrawRect(FLinearColor::White, MapOrigin.X + MapSize / 2 - 3, MapOrigin.Y + MapSize / 2 - 3, 6 * HudScale, 6 * HudScale);
    const FName Realm = State->GetRealm() == EWarRealm::Aegis ? FName(TEXT("aegis"))
        : State->GetRealm() == EWarRealm::Riftbound ? FName(TEXT("riftbound")) : NAME_None;
    const auto& Snapshot = State->GetInventory();
    float QuestY = FrameTop + FrameHeight + 16 * HudScale;
    int32 Tracked = 0;
    for (const auto& QuestProgress : Snapshot.Quests)
    {
        if (QuestProgress.Status != TEXT("active") && QuestProgress.Status != TEXT("ready_to_turn_in")) continue;
        FWarQuestDefinition Definition; FString Error;
        if (!Content->GetQuest(QuestProgress.Id, Definition, Error)) continue;
        if (++Tracked > 3) break;
        DrawText(Definition.Title.Left(42), FLinearColor(0.95f, 0.82f, 0.4f), Left, QuestY, HudFont, HudScale);
        QuestY += 23 * HudScale;
        if (QuestProgress.Status == TEXT("ready_to_turn_in"))
        {
            DrawText(TEXT("Ready to turn in [")+KeyLabel(TEXT("Quests"))+TEXT("]"), FLinearColor::White, Left, QuestY, HudFont, HudScale);
            QuestY += 23 * HudScale;
        }
        else for (const auto& Objective : Definition.Objectives)
        {
            if (QuestY > Footer - 35 * HudScale) break;
            DrawText(FString::Printf(TEXT("%s: %d / %d"), *Objective.Description.Left(32), QuestProgress.GetCount(Objective.Id), Objective.Required),
                FLinearColor::White, Left, QuestY, HudFont, HudScale);
            QuestY += 23 * HudScale;
        }
        QuestY += 10 * HudScale;
    }
    for (TActorIterator<AWarEnemy> It(GetWorld()); It; ++It)
    {
        if (!It->IsContentReady() || It->IsDead() || It->ZoneId != State->GetCurrentZone()
            || FVector::DistSquared(It->GetActorLocation(), Character->GetActorLocation()) > FMath::Square(3500.0)
            || !It->HasLineOfSight(Character)) continue;
        FVector2D Point;
        if (!Controller->ProjectWorldLocationToScreen(It->GetActorLocation() + FVector(0, 0, 125), Point, true)) continue;
        const float Width = 120 * HudScale;
        DrawText(FString::Printf(TEXT("%s  %d"), *It->GetDefinition().Name, It->GetDefinition().Level),
            FLinearColor(1, 0.6f, 0.45f), Point.X - Width / 2, Point.Y - 20 * HudScale, HudFont, HudScale);
        DrawRect(FLinearColor(0.08f, 0.025f, 0.025f), Point.X - Width / 2, Point.Y, Width, 7 * HudScale);
        DrawRect(FLinearColor(0.7f, 0.09f, 0.07f), Point.X - Width / 2, Point.Y,
            Width * FMath::Clamp(It->GetHealth() / It->GetDefinition().MaxHealth, 0.f, 1.f), 7 * HudScale);
    }
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
