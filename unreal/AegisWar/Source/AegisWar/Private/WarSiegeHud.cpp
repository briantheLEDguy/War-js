#include "WarSiegeHud.h"
#include "WarSiegeBattlefield.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "GameFramework/PlayerController.h"
void AWarSiegeHud::DrawHUD()
{
    Super::DrawHUD();
    const auto* GS = GetWorld()->GetGameState<AWarSiegeGameState>(); if (!Canvas || !GS) return;
    const auto& S = GS->Siege; const float X = Canvas->SizeX * .34f;
    DrawRect(FLinearColor(0,0,0,.8f), X - 12, 12, Canvas->SizeX * .4f, 160);
    const TCHAR* Names[] = {TEXT("Lower city"), TEXT("Citadel courtyard"), TEXT("Inner citadel")};
    const int32 Seconds = FMath::Max(0, FMath::CeilToInt(S.Remaining));
    DrawText(FString::Printf(TEXT("%s | %dv%d | %s%d:%02d"), Names[FMath::Clamp(S.Stage,0,2)], S.Capacity, S.Capacity,
        S.bOvertime ? TEXT("Overtime ") : TEXT(""), Seconds / 60, Seconds % 60), FLinearColor::White, X, 20);
    DrawText(GS->Status, FLinearColor::White, X, 45);
    DrawText(FString::Printf(TEXT("Objective %.0f%% | Respawn wave %.0fs"), S.Progress * 100,
        FMath::Max(0., GS->NextWaveAt - GS->GetServerWorldTimeSeconds())), FLinearColor::White, X, 70);
    const TCHAR* Optional[] = {TEXT("Sabotage emplacement"), TEXT("Capture reinforcement post"), TEXT("Sabotage rally beacon")};
    DrawText(FString::Printf(TEXT("Optional: %s — %s %.0f%%"), Optional[FMath::Clamp(S.Stage,0,2)],
        S.bOptionalComplete ? TEXT("Complete") : TEXT("Progress"), S.OptionalProgress * 100), FLinearColor(.8,.8,.4), X, 95);
    DrawText(GS->CommanderAction, FLinearColor(1,.35,.2), X, 120);
    if (S.Phase == EWarSiegePhase::Active && PlayerOwner)
    {
        const auto Marker = [&](const FVector& Location, const FString& Label, FLinearColor Color)
        {
            FVector2D Screen;
            if (PlayerOwner->ProjectWorldLocationToScreen(Location + FVector(0,0,150), Screen)) DrawText(Label, Color, Screen.X, Screen.Y);
        };
        Marker(GS->ObjectiveLocation, TEXT("MAIN OBJECTIVE"), FLinearColor::Yellow);
        if (!S.bOptionalComplete) Marker(GS->OptionalLocation, TEXT("OPTIONAL"), FLinearColor(.6,.8,1));
        if (GS->HazardUntil > GS->GetServerWorldTimeSeconds()) Marker(GS->HazardLocation, TEXT("DANGER — MOVE AWAY"), FLinearColor::Red);
    }
    float Y = 190;
    for (const auto& Label : GS->RosterLabels) { DrawText(Label, FLinearColor(.7,.8,.9), 16, Y); Y += 16; }
}
