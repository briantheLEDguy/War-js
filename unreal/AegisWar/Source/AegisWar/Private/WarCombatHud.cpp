#include "WarQuestHud.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "WarEnemy.h"
#include "WarAttributeSet.h"
#include "WarAbilityRuntime.h"
#include "WarTargetReticle.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"

void AWarQuestHud::DrawCombatFeedback()
{
    auto* PC = Cast<AWarPlayerController>(GetOwningPlayerController());
    if (!Canvas || !PC || !GEngine) return;
    const float Scale = FMath::Clamp(Canvas->SizeY / 900.f, .8f, 1.5f);
    const float Width = 360 * Scale, X = (Canvas->SizeX - Width) / 2, Y = 16 * Scale;
    AActor* Target = PC->GetCombatTarget();
    if (Target && !PC->IsMoveInputIgnored() && !PC->IsWorldEditorOpen() && !PC->IsEditingUi() && PC->LineOfSightTo(Target))
    {
        // Only the character mesh bounds: camera booms, effects and attachments can dwarf the body.
        const auto* Mesh = Target->FindComponentByClass<USkeletalMeshComponent>();
        FBox Body = Mesh && Mesh->GetSkeletalMeshAsset() ? Mesh->Bounds.GetBox() : Target->GetComponentsBoundingBox(true);
        if (!Mesh || !Mesh->GetSkeletalMeshAsset())
            if (const auto* StaticMesh = Target->FindComponentByClass<UStaticMeshComponent>(); StaticMesh && StaticMesh->GetStaticMesh())
                Body = StaticMesh->Bounds.GetBox();
        FBox2D Screen(ForceInit);
        bool bProjected = Body.IsValid != 0;
        for (int32 Corner = 0; Corner < 8 && bProjected; ++Corner)
        {
            FVector2D Point;
            const FVector Position(Corner & 1 ? Body.Max.X : Body.Min.X,
                Corner & 2 ? Body.Max.Y : Body.Min.Y, Corner & 4 ? Body.Max.Z : Body.Min.Z);
            bProjected = PC->ProjectWorldLocationToScreen(Position, Point, true);
            if (bProjected) Screen += Point;
        }
        // Do not turn offscreen/behind-camera targets into a misleading marker at the screen edge.
        if (bProjected && Screen.Max.X > 0 && Screen.Min.X < Canvas->SizeX && Screen.Max.Y > 0 && Screen.Min.Y < Canvas->SizeY)
        {
            const auto Lines = WarTargetReticle::Corners(Screen.ExpandBy(8 * Scale), Scale);
            const FLinearColor Color = WarTargetReticle::Color(PC->IsEnemyCombatTarget(Target));
            for (const auto& Line : Lines)
                DrawLine(Line.Key.X, Line.Key.Y, Line.Value.X, Line.Value.Y, FLinearColor(0, 0, 0, .9f), 7 * Scale);
            for (const auto& Line : Lines)
                DrawLine(Line.Key.X, Line.Key.Y, Line.Value.X, Line.Value.Y, Color, 3 * Scale);
        }
    }
    float Health = 0, Maximum = 0; FString Name; bool Allied = false;
    const UWarAbilityRuntime* Runtime = nullptr;
    if (const auto* Enemy = Cast<AWarEnemy>(Target))
    { Name = Enemy->GetDefinition().Name; Health = Enemy->GetHealth(); Maximum = Enemy->GetDefinition().MaxHealth; }
    else if (const auto* Character = Cast<AWarCharacter>(Target))
        if (const auto* State = Character->GetPlayerState<AWarPlayerState>())
        {
            Name = State->GetPlayerName(); Health = State->GetAttributes()->GetHealth(); Maximum = State->GetAttributes()->GetMaxHealth();
            Runtime = State->GetClassAbilities();
            const auto* LocalState = PC->GetPlayerState<AWarPlayerState>(); Allied = LocalState && LocalState->GetRealm() == State->GetRealm();
        }
    if (Target && Maximum > 0)
    {
        DrawRect(FLinearColor(.03f,.025f,.02f,.94f), X - 10, Y - 5, Width + 20, 108 * Scale);
        DrawText((Allied ? TEXT("ALLY  ") : TEXT("ENEMY  ")) + Name.Left(32), FLinearColor(1,.85f,.55f), X, Y, GEngine->GetMediumFont(), Scale);
        DrawRect(FLinearColor(.12f,.1f,.08f), X, Y + 28 * Scale, Width, 20 * Scale);
        DrawRect(WarTargetReticle::Color(!Allied), X, Y + 28 * Scale,
            Width * FMath::Clamp(Health / Maximum, 0.f, 1.f), 20 * Scale);
        DrawText(FString::Printf(TEXT("%.0f / %.0f"), Health, Maximum), FLinearColor::White, X + 5, Y + 29 * Scale, GEngine->GetSmallFont(), Scale);
        if (Runtime && Runtime->GetPublicCastEnd() > Runtime->Now())
        {
            const float Progress = FMath::Clamp(float((Runtime->Now() - Runtime->GetPublicCastStart()) /
                FMath::Max(.001, Runtime->GetPublicCastEnd() - Runtime->GetPublicCastStart())), 0.f, 1.f);
            DrawText(Runtime->GetPublicCastLabel().Left(28) + TEXT(" — interruptible"), FLinearColor(1,.8f,.3f), X, Y + 55 * Scale, GEngine->GetSmallFont(), Scale);
            DrawRect(FLinearColor(.18f,.14f,.06f), X, Y + 78 * Scale, Width, 9 * Scale);
            DrawRect(FLinearColor(.85f,.6f,.15f), X, Y + 78 * Scale, Width * Progress, 9 * Scale);
        }
    }
    float NoticeY = Canvas->SizeY * .52f;
    for (const auto& Notice : PC->GetCombatNotices())
    {
        if (Notice.Expires <= GetWorld()->GetTimeSeconds()) continue;
        const bool bCritical=Notice.Kind==TEXT("CriticalHit");
        const float Age=GetWorld()->GetTimeSeconds()-(Notice.Expires-3);
        if ((Notice.Kind==TEXT("Hit") || bCritical) && Age<.18f)
        {
            const float Size=(bCritical ? 15.f : 10.f)*Scale, Gap=5.f*Scale;
            const FLinearColor Flash(1,bCritical ? .55f : .85f,.25f,1-Age/.18f);
            for (int32 SX : {-1,1}) for (int32 SY : {-1,1})
                DrawLine(Canvas->SizeX*.5f+SX*Gap,Canvas->SizeY*.5f+SY*Gap,Canvas->SizeX*.5f+SX*Size,Canvas->SizeY*.5f+SY*Size,Flash,bCritical ? 3.f : 2.f);
        }
        const FLinearColor Color = Notice.Kind == TEXT("Heal") ? FLinearColor(.4f,1,.5f)
            : Notice.Kind == TEXT("Interrupt") ? FLinearColor(1,.8f,.2f)
            : Notice.Kind == TEXT("Guarded") ? FLinearColor(.65f,.8f,1) : FLinearColor::White;
        const FString Text = Notice.Kind == TEXT("Interrupt") ? TEXT("INTERRUPT — ") + Notice.Label
            : FString::Printf(TEXT("%s %.0f — %s"), *Notice.Kind.ToString(), Notice.Amount, *Notice.Label);
        DrawRect(FLinearColor(.018f,.014f,.01f,.9f),Canvas->SizeX-356*Scale,NoticeY-2*Scale,350*Scale,22*Scale);
        DrawText(Text.Left(48), bCritical ? FLinearColor(1,.65f,.15f) : Color, Canvas->SizeX - 350 * Scale, NoticeY, GEngine->GetSmallFont(), Scale*(bCritical ? 1.15f : 1.f));
        NoticeY += 22 * Scale;
    }
}
