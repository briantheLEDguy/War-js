#include "WarSiegeHud.h"
#include "WarSiegeBattlefield.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "GameFramework/PlayerController.h"
#include "WarPlayerState.h"
#include "WarPlayerController.h"
void AWarSiegeHud::DrawHUD()
{
    Super::DrawHUD();
    const auto* GS = GetWorld()->GetGameState<AWarSiegeGameState>(); if (!Canvas || !GS) return;
    if (GS->bDevelopmentLobby && (GS->Siege.Phase == EWarSiegePhase::Waiting || GS->Siege.Phase == EWarSiegePhase::Finished)) return;
    const auto& S = GS->Siege;
    const float Scale=FMath::Clamp(Canvas->SizeY/1080.f,.85f,1.25f);
    const float Width=400*Scale, X=Canvas->SizeX-Width-20;
    // Match the base HUD's radar scale, including its caption and a small gap.
    const float Top=260*FMath::Clamp(Canvas->SizeY/900.f,.65f,1.5f);
    DrawRect(FLinearColor(.018f,.014f,.01f,.9f),X-12,Top,Width+12,185*Scale);
    const TCHAR* Names[] = {TEXT("Lower city"), TEXT("Citadel courtyard"), TEXT("Inner citadel")};
    const int32 Seconds = FMath::Max(0, FMath::CeilToInt(S.Remaining));
    DrawText(FString::Printf(TEXT("%s | %dv%d | %s%d:%02d"), Names[FMath::Clamp(S.Stage,0,2)], S.Capacity, S.Capacity,
        S.bOvertime ? TEXT("Overtime ") : TEXT(""), Seconds / 60, Seconds % 60), FLinearColor::White, X, Top + 8);
    const auto* PS = PlayerOwner ? PlayerOwner->GetPlayerState<AWarPlayerState>() : nullptr;
    const bool Defender = PS && PS->GetRealm() == EWarRealm::Aegis;
    DrawText(Defender ? TEXT("DEFEND: hold the gate until time expires") : TEXT("ATTACK: escort engineers and breach the gate"), FLinearColor(.95,.8,.4), X, Top + 33, nullptr, .85f);
    DrawText(GS->Status, FLinearColor::White, X, Top + 55);
    DrawText(FString::Printf(TEXT("Objective %.0f%% | Respawn wave %.0fs"), S.Progress * 100,
        FMath::Max(0., GS->NextWaveAt - GS->GetServerWorldTimeSeconds())), FLinearColor::White, X, Top + 78);
    if (GS->bContested) DrawText(TEXT("CONTESTED — progress paused"), FLinearColor(1,.5,.2), X, Top + 100);
    else if (GS->CrewMaxHealth > 0) DrawText(FString::Printf(TEXT("Engineers: %.0f / %.0f health"), GS->CrewHealth, GS->CrewMaxHealth), FLinearColor(.6,1,.65), X, Top + 100);
    const TCHAR* Optional[] = {TEXT("Sabotage emplacement"), TEXT("Capture reinforcement post"), TEXT("Sabotage rally beacon")};
    DrawText(FString::Printf(TEXT("Optional: %s — %s %.0f%%"), Optional[FMath::Clamp(S.Stage,0,2)],
        S.bOptionalComplete ? TEXT("Complete") : TEXT("Progress"), S.OptionalProgress * 100), FLinearColor(.8,.8,.4), X, Top + 124);
    DrawText(GS->CommanderAction, FLinearColor(1,.35,.2), X, Top + 148);
    if (S.Phase == EWarSiegePhase::Active && PlayerOwner)
    {
        const auto Marker = [&](const FVector& Location, const FString& Label, FLinearColor Color)
        {
            FVector2D Screen;
            if (PlayerOwner->ProjectWorldLocationToScreen(Location + FVector(0,0,150), Screen))
            {
                // World labels must not paint over the objective panel's text.
                float LabelWidth=0,LabelHeight=0; GetTextSize(Label,LabelWidth,LabelHeight);
                if (Screen.X+LabelWidth>=X-12 && Screen.Y+LabelHeight>=Top && Screen.Y<=Top+185*Scale) return;
                DrawText(Label, Color, Screen.X, Screen.Y);
            }
        };
        Marker(GS->ObjectiveLocation, TEXT("MAIN OBJECTIVE"), FLinearColor::Yellow);
        if (!S.bOptionalComplete) Marker(GS->OptionalLocation, TEXT("OPTIONAL"), FLinearColor(.6,.8,1));
        if (GS->HazardUntil > GS->GetServerWorldTimeSeconds()) Marker(GS->HazardLocation, TEXT("DANGER — MOVE AWAY"), FLinearColor::Red);
    }
    if (S.Phase==EWarSiegePhase::Active) if (auto* PC=Cast<AWarPlayerController>(PlayerOwner))
    {
        const TCHAR* Orders[]={TEXT("Follow"),TEXT("Attack"),TEXT("Hold"),TEXT("Optional")};
        DrawText(FString::Printf(TEXT("Your squad: %d | %s"),PC->SiegeSquadCount,Orders[FMath::Min(int32(PC->SiegeSquadOrder),3)]),FLinearColor::White,X,Top+187*Scale);
        for (int32 I=0;I<4;++I)
        {
            const float Left=X+I*98*Scale, Y=Top+211*Scale;
            DrawRect(PC->SiegeSquadOrder==I ? FLinearColor(.3f,.22f,.06f,.95f) : FLinearColor(.05f,.06f,.08f,.95f),Left,Y,93*Scale,28*Scale);
            DrawText(Orders[I],FLinearColor::White,Left+5,Y+5,nullptr,.85f);
            if (I!=3 || !S.bOptionalComplete) AddHitBox(FVector2D(Left,Y),FVector2D(93*Scale,28*Scale),FName(*FString::Printf(TEXT("Squad%d"),I)),true);
        }
    }
    // The full roster belongs in preparation/results; keep the combat view clear.
}

void AWarSiegeHud::NotifyHitBoxClick(FName BoxName)
{
    Super::NotifyHitBoxClick(BoxName);
    const FString Name=BoxName.ToString();
    const auto* GS=GetWorld()->GetGameState<AWarSiegeGameState>();
    if (Name.StartsWith(TEXT("Squad")) && GS) if (auto* PC=Cast<AWarPlayerController>(PlayerOwner))
        PC->ServerSiegeSquadOrder(GS->RoundId,uint8(FCString::Atoi(*Name.Mid(5))));
}
