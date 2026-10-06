#include "WarQuestHud.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "WarEnemy.h"
#include "WarAttributeSet.h"
#include "WarAbilityRuntime.h"
#include "WarCombatUiDrawing.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Canvas.h"

void AWarQuestHud::DrawCombatFeedback()
{
    auto* PC=Cast<AWarPlayerController>(GetOwningPlayerController());
    if (!Canvas || !PC || PC->IsEditingUi()) return;
    const auto& Settings=PC->GetCombatUiSettings(); FWarCombatUiDrawList Draw;
    const float Scale=FMath::Clamp(Canvas->SizeY/900.f,.8f,1.5f);
    const FVector2D View(Canvas->SizeX,Canvas->SizeY);
    DrawOverheadHealthBars();
    const bool WorldVisible=!PC->IsMoveInputIgnored() && !PC->IsWorldEditorOpen();
    if (WorldVisible) for (const auto& N:PC->GetFloatingCombatNumbers())
    {
        const APawn* Self=PC->GetPawn(); const auto* State=PC->GetPlayerState<AWarPlayerState>();
        if (!Self || !State || FVector::DistSquared(Self->GetActorLocation(),N.Anchor)>FMath::Square(5000.0)) continue;
        if (N.Recipient.IsValid())
        {
            const auto* Recipient=N.Recipient.Get();
            if (Recipient->IsHidden() || !PC->LineOfSightTo(Recipient)) continue;
            if (const auto* Npc=Cast<AWarEnemy>(Recipient); Npc && (!Npc->IsContentReady() || Npc->ZoneId!=State->GetCurrentZone())) continue;
            if (const auto* Character=Cast<AWarCharacter>(Recipient))
            {
                const auto* Other=Character->GetPlayerState<AWarPlayerState>();
                if (!Other || !Character->IsVisualReady() || Other->GetCurrentZone()!=State->GetCurrentZone()) continue;
            }
        }
        FVector2D Head;
        if (PC->ProjectWorldLocationToScreen(N.Anchor,Head,true) && Head.X>=0 && Head.Y>=0 && Head.X<View.X && Head.Y<View.Y)
            WarCombatUi::Number(Draw,Settings,N,Head,Scale);
    }
    AActor* Target=PC->GetCombatTarget(); const bool Enemy=Target && PC->IsEnemyCombatTarget(Target);
    if (Target && WorldVisible && PC->LineOfSightTo(Target))
    {
        const auto* Mesh=Target->FindComponentByClass<USkeletalMeshComponent>();
        FBox Body=Mesh && Mesh->GetSkeletalMeshAsset()?Mesh->Bounds.GetBox():Target->GetComponentsBoundingBox(true);
        if (!Mesh || !Mesh->GetSkeletalMeshAsset())
            if (const auto* Static=Target->FindComponentByClass<UStaticMeshComponent>(); Static && Static->GetStaticMesh()) Body=Static->Bounds.GetBox();
        FBox2D Screen(ForceInit); bool Projected=Body.IsValid!=0;
        for (int32 C=0;C<8 && Projected;++C)
        {
            FVector2D P; Projected=PC->ProjectWorldLocationToScreen(FVector(C&1?Body.Max.X:Body.Min.X,C&2?Body.Max.Y:Body.Min.Y,C&4?Body.Max.Z:Body.Min.Z),P,true);
            if (Projected) Screen+=P;
        }
        if (Projected && Screen.Max.X>0 && Screen.Min.X<View.X && Screen.Max.Y>0 && Screen.Min.Y<View.Y) WarCombatUi::Reticle(Draw,Settings,Enemy,Screen,Scale);
    }
    float Health=0,Max=0,CastProgress=0; FString Name,CastLabel;
    if (const auto* Npc=Cast<AWarEnemy>(Target)) { Health=Npc->GetHealth(); Max=Npc->GetDefinition().MaxHealth; Name=Npc->GetDefinition().Name; }
    else if (const auto* Character=Cast<AWarCharacter>(Target)) if (const auto* State=Character->GetPlayerState<AWarPlayerState>())
    {
        Name=State->GetPlayerName(); Health=State->GetAttributes()->GetHealth(); Max=State->GetAttributes()->GetMaxHealth();
        const auto* Runtime=State->GetClassAbilities();
        if (Runtime && Runtime->GetPublicCastEnd()>Runtime->Now())
        {
            CastLabel=Runtime->GetPublicCastLabel()+TEXT(" - interruptible");
            CastProgress=FMath::Clamp(float((Runtime->Now()-Runtime->GetPublicCastStart())/FMath::Max(.001,Runtime->GetPublicCastEnd()-Runtime->GetPublicCastStart())),0.f,1.f);
        }
    }
    if (Target && Max>0) WarCombatUi::Panel(Draw,Settings,Enemy,View,Scale,Name,Health,Max,CastLabel,CastProgress);
    WarCombatUi::Notices(Draw,Settings,View,Scale,PC->GetCombatNotices(),GetWorld()->GetTimeSeconds());
    WarCombatUi::Canvas(this,Canvas,Draw);
}
