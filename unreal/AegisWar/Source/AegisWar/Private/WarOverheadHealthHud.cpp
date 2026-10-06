#include "WarQuestHud.h"
#include "WarPlayerController.h"
#include "WarOverheadHealth.h"
#include "WarTargetReticle.h"
#include "WarCombatUiDrawing.h"
#include "Engine/Canvas.h"
#include "EngineUtils.h"

void AWarQuestHud::DrawOverheadHealthBars()
{
    auto* PC = Cast<AWarPlayerController>(GetOwningPlayerController());
    if (!Canvas || !PC || PC->IsMoveInputIgnored() || PC->IsWorldEditorOpen() || PC->IsEditingUi()) return;
    const float Scale = FMath::Clamp(Canvas->SizeY / 900.f, .8f, 1.5f);
    FWarCombatUiDrawList Draw; const auto& Settings=PC->GetCombatUiSettings();
    for (TActorIterator<APawn> It(GetWorld()); It; ++It)
    {
        FWarOverheadHealth Health;
        if (!WarOverheadHealth::Read(PC, *It, Health)) continue;
        FVector2D Head;
        if (!PC->ProjectWorldLocationToScreen(WarFloatingCombatText::HeadAnchor(*It), Head, true)) continue;
        FWarCombatUiDrawList One; WarCombatUi::HealthBar(One,Settings,Health.bEnemy,Head,Health.Fraction,Scale);
        const auto* Bounds=One.Handles.Find(WarCombatUi::Id(EWarCombatUiPart::OverheadHealth,Health.bEnemy));
        const auto Rect=Bounds?*Bounds:FBox2D(ForceInit);
        // Test sight only for on-screen, eligible recipients. No through-wall nameplates.
        if (!Rect.bIsValid || Rect.Min.X<0 || Rect.Min.Y<0 || Rect.Max.X>Canvas->SizeX || Rect.Max.Y>Canvas->SizeY || One.Items.IsEmpty() || !PC->LineOfSightTo(*It)) continue;
        Draw.Items.Append(One.Items);
    }
    WarCombatUi::Canvas(this,Canvas,Draw);
}
