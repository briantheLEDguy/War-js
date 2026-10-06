#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "Engine/World.h"
#include "WarImpactCameraModifier.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundWaveProcedural.h"
#include "Components/AudioComponent.h"
#include "TimerManager.h"

void AWarPlayerController::SetCombatShakeIntensity(float Value)
{
    CombatShakeIntensity=FMath::IsFinite(Value) ? FMath::Clamp(Value,0.f,1.f) : .25f;
    if (CombatShakeIntensity==0 && PlayerCameraManager)
        if (auto* Modifier=Cast<UWarImpactCameraModifier>(PlayerCameraManager->FindCameraModifierByClass(UWarImpactCameraModifier::StaticClass()))) Modifier->Stop();
}

void AWarPlayerController::SendCombatNotice(FName Kind, const FString& Label, float Amount, AActor* Recipient)
{
    if (GetWorld()->GetTimeSeconds() >= CombatNoticeWindow)
    { CombatNoticeWindow = GetWorld()->GetTimeSeconds() + 1; CombatNoticeCount = 0; }
    if (CombatNoticeCount >= 128) return;
    if (HasAuthority() && WarCombatFeedback::Valid(Kind, Amount) && NextCombatSerial < MAX_uint32)
    {
        ++CombatNoticeCount;
        const bool bOutgoing = IsValid(Recipient);
        const auto* RecipientCharacter=Cast<AWarCharacter>(Recipient);
        const auto* Other=RecipientCharacter?RecipientCharacter->GetPlayerState<AWarPlayerState>():nullptr;
        const auto* Self=GetPlayerState<AWarPlayerState>();
        const bool bEnemy=Recipient!=GetPawn() && !(Self && Other && Self->GetRealm()!=EWarRealm::None && Self->GetRealm()==Other->GetRealm());
        ClientCombatNotice(++NextCombatSerial, Kind, Label.Left(80), Amount,
            bOutgoing ? Recipient->GetUniqueID() : 0, bOutgoing ? Recipient : nullptr,
            bOutgoing ? WarFloatingCombatText::HeadAnchor(Recipient) : FVector::ZeroVector, bEnemy);
    }
}
void AWarPlayerController::ClientCombatNotice_Implementation(uint32 Serial, FName Kind, const FString& Label, float Amount,
    uint32 RecipientId, AActor* Recipient, FVector Anchor, bool bEnemy)
{
    const double Time=GetWorld()->GetTimeSeconds();
    if (!WarCombatFeedback::Append(CombatNotices,LastCombatSerial,Serial,Kind,Label,Amount,Time)) return;
    const auto Part=Kind==TEXT("Heal")?EWarCombatUiPart::Healing:Kind==TEXT("CriticalHit")?EWarCombatUiPart::Critical:EWarCombatUiPart::Damage;
    WarFloatingCombatText::Add(FloatingCombatNumbers, RecipientId, Recipient, Anchor, Kind, Amount, Time,bEnemy,
        &GetCombatUiSettings().Styles[WarCombatUi::Id(Part,bEnemy)]);
    if (Kind!=TEXT("Hit") && Kind!=TEXT("CriticalHit")) return;
    const bool bCritical=Kind==TEXT("CriticalHit");
    if (PlayerCameraManager && CombatShakeIntensity>0)
    {
        auto* Modifier=Cast<UWarImpactCameraModifier>(PlayerCameraManager->FindCameraModifierByClass(UWarImpactCameraModifier::StaticClass()));
        if (!Modifier) Modifier=Cast<UWarImpactCameraModifier>(PlayerCameraManager->AddNewCameraModifier(UWarImpactCameraModifier::StaticClass()));
        if (Modifier) Modifier->Pulse(CombatShakeIntensity*(bCritical ? 1.f : .7f));
    }
    if (Time<NextImpactSound || GetInterfaceVolume()<=0 || GetNetMode()==NM_DedicatedServer) return;
    NextImpactSound=Time+.06;
    // Original synthesized impact: no external sound pack or licensed asset dependency.
    auto* Sound=NewObject<USoundWaveProcedural>(this);
    Sound->SetSampleRate(WarCombatFeedback::ImpactSampleRate); Sound->NumChannels=1; Sound->Duration=.18f; Sound->bLooping=false;
    const TArray<int16> Samples=WarCombatFeedback::ImpactSamples(Serial,bCritical);
    Sound->QueueAudio(reinterpret_cast<const uint8*>(Samples.GetData()),Samples.Num()*sizeof(int16));
    if (auto* Audio=UGameplayStatics::SpawnSound2D(this,Sound,bCritical ? .8f : .55f))
    {
        FTimerHandle StopSound; const TWeakObjectPtr<UAudioComponent> WeakAudio(Audio);
        GetWorldTimerManager().SetTimer(StopSound,[WeakAudio] { if (WeakAudio.IsValid()) WeakAudio->Stop(); },.22f,false);
    }
}
