#include "WarFloatingCombatText.h"
#include "WarCombatFeedback.h"
#include "WarCombatUiSettings.h"
#include "GameFramework/Character.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"

FVector WarFloatingCombatText::HeadAnchor(const AActor* Recipient)
{
    if (!IsValid(Recipient)) return FVector::ZeroVector;
    FBox Body(ForceInit);
    if (const auto* Mesh = Recipient->FindComponentByClass<USkeletalMeshComponent>(); Mesh && Mesh->GetSkeletalMeshAsset())
        Body = Mesh->Bounds.GetBox();
    else if (const auto* Static = Recipient->FindComponentByClass<UStaticMeshComponent>(); Static && Static->GetStaticMesh())
        Body = Static->Bounds.GetBox();
    else if (const auto* Character = Cast<ACharacter>(Recipient))
        Body = Character->GetCapsuleComponent()->Bounds.GetBox();
    // Exclude weapons, camera booms and effects from the overhead anchor.
    return Body.IsValid ? FVector(Body.GetCenter().X, Body.GetCenter().Y, Body.Max.Z + 12)
        : Recipient->GetActorLocation() + FVector(0, 0, 100);
}

void WarFloatingCombatText::Advance(TArray<FWarFloatingCombatNumber>& Numbers, double Now)
{
    if (!FMath::IsFinite(Now)) return;
    for (auto& Number : Numbers)
    {
        // A clock reset (travel) must not carry old combat text into another world.
        Number.Progress = Now < Number.Updated ? 1.f
            : Number.Progress + static_cast<float>(Now - Number.Updated) * Number.Speed / Number.Lifetime;
        Number.Updated = Now;
        if (Number.Recipient.IsValid()) Number.Anchor = HeadAnchor(Number.Recipient.Get());
    }
    Numbers.RemoveAll([](const auto& Number) { return Number.Progress >= 1.f; });
}

bool WarFloatingCombatText::Add(TArray<FWarFloatingCombatNumber>& Numbers, uint32 RecipientId, AActor* Recipient,
    FVector Anchor, FName Kind, float Amount, double Now, bool bEnemy, const FWarCombatUiStyle* Style)
{
    if (!RecipientId || !WarCombatFeedback::Valid(Kind, Amount) || !FMath::IsFinite(Now) || Anchor.ContainsNaN()
        || (Kind != TEXT("Hit") && Kind != TEXT("CriticalHit") && Kind != TEXT("Heal"))) return false;
    const auto Part=Kind==TEXT("Heal")?EWarCombatUiPart::Healing:Kind==TEXT("CriticalHit")?EWarCombatUiPart::Critical:EWarCombatUiPart::Damage;
    const auto Settings=Style?WarCombatUi::Sanitize(WarCombatUi::Id(Part,bEnemy),*Style):WarCombatUi::Defaults(WarCombatUi::Id(Part,bEnemy));
    if (!Settings.Visible) return false;
    Advance(Numbers, Now);
    int32 Count = 0, Recent = 0, Lane = 0;
    for (const auto& Number : Numbers)
        if (Number.RecipientId == RecipientId)
        {
            ++Count;
            if (Now - Number.Created <= .35) ++Recent;
            Lane = (Number.Lane + 1) % 3;
        }
    const float BurstFraction = FMath::Min(Recent, 4) / 4.f;
    const float Speed = 1.f + (Settings.Burst-1)*BurstFraction;
    for (auto& Number : Numbers)
        if (Number.RecipientId == RecipientId)
        {
            Number.Speed = FMath::Max(Number.Speed, 1.f+(Number.MaxBurst-1)*BurstFraction);
            // Reusing a lane pushes its earlier number up, including simultaneous procs.
            if (Number.Lane == Lane) Number.Progress = FMath::Max(Number.Progress, .4f);
        }
    if (Count >= MaxPerRecipient)
        Numbers.RemoveAt(Numbers.IndexOfByPredicate([RecipientId](const auto& Number) { return Number.RecipientId == RecipientId; }));
    while (Numbers.Num() >= MaxNumbers) Numbers.RemoveAt(0);
    FWarFloatingCombatNumber Number;
    Number.Recipient = Recipient; Number.RecipientId = RecipientId; Number.Anchor = Anchor;
    Number.Kind = Kind; Number.Amount = Amount; Number.Created = Number.Updated = Now;
    Number.Speed = Speed; Number.Lane = Lane;
    Number.bEnemy=bEnemy; Number.Lifetime=Settings.Lifetime; Number.Rise=Settings.Rise; Number.MaxBurst=Settings.Burst;
    Numbers.Add(Number);
    return true;
}

FVector2D WarFloatingCombatText::Offset(const FWarFloatingCombatNumber& Number)
{
    const float Side = Number.Lane == 0 ? 0.f : Number.Lane == 1 ? -1.f : 1.f;
    return FVector2D(Side * (32.f + 6.f * Number.Progress), -8.f - Number.Rise * Number.Progress);
}

float WarFloatingCombatText::Opacity(const FWarFloatingCombatNumber& Number)
{
    return FMath::Clamp((1.f - Number.Progress) / .3f, 0.f, 1.f);
}
