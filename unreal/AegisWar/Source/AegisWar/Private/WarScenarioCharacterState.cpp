#include "WarPlayerState.h"
#include "WarAbilityRuntime.h"
#include "WarAbilityCatalog.h"
#include "WarAttributeSet.h"
#include "Dom/JsonObject.h"

TSharedPtr<FJsonObject> UWarAbilityRuntime::CaptureScenarioState() const
{
    auto State=MakeShared<FJsonObject>();State->SetNumberField(TEXT("resource"),Resource);
    State->SetNumberField(TEXT("globalCooldown"),FMath::Max(0.,GcdUntil-Now()));
    TArray<TSharedPtr<FJsonValue>> Entries;
    for (const auto& Cooldown:Cooldowns) if (Cooldown.Until>Now())
    {
        auto Entry=MakeShared<FJsonObject>();Entry->SetStringField(TEXT("id"),Cooldown.Id.ToString());
        Entry->SetNumberField(TEXT("remaining"),Cooldown.Until-Now());Entries.Add(MakeShared<FJsonValueObject>(Entry));
    }
    State->SetArrayField(TEXT("cooldowns"),Entries);return State;
}
void UWarAbilityRuntime::RestoreScenarioState(const TSharedPtr<FJsonObject>& State)
{
    if (!State || !GetOwner()->HasAuthority()) return;
    const auto Kit=Catalog() ? Catalog()->Kit(Career) : TArray<const FWarAbilityDefinition*>();
    double Value=0;
    if (State->TryGetNumberField(TEXT("resource"),Value) && !Kit.IsEmpty()) Resource=FMath::Clamp(float(Value),0.f,Kit[0]->ResourceMax);
    if (State->TryGetNumberField(TEXT("globalCooldown"),Value)) GcdUntil=Now()+FMath::Max(0.,Value);
    const TArray<TSharedPtr<FJsonValue>>* Entries=nullptr;
    if (State->TryGetArrayField(TEXT("cooldowns"),Entries))
    {
        Cooldowns.Reset();
        for (const auto& Entry:*Entries)
        {
            const auto Object=Entry->AsObject();FString Id;double Remaining=0;
            if (Object && Object->TryGetStringField(TEXT("id"),Id) && Object->TryGetNumberField(TEXT("remaining"),Remaining) && Remaining>0)
            { FWarAbilityCooldown Cooldown;Cooldown.Id=FName(*Id);Cooldown.Until=Now()+Remaining;Cooldowns.Add(Cooldown); }
        }
    }
    GetOwner()->ForceNetUpdate();
}
TSharedPtr<FJsonObject> AWarPlayerState::CaptureScenarioState() const
{
    auto State=MakeShared<FJsonObject>();State->SetNumberField(TEXT("health"),Attributes->GetHealth());
    State->SetNumberField(TEXT("mana"),Attributes->GetMana());State->SetObjectField(TEXT("abilities"),ClassAbilities->CaptureScenarioState());
    const auto Serialize=[](const TSet<FGuid>& Receipts) {
        TArray<TSharedPtr<FJsonValue>> Values;for (const auto& Id:Receipts) Values.Add(MakeShared<FJsonValueString>(Id.ToString()));return Values;
    };
    State->SetArrayField(TEXT("rewards"),Serialize(RewardReceipts));State->SetArrayField(TEXT("questKills"),Serialize(QuestKillReceipts));return State;
}
void AWarPlayerState::RestoreScenarioState(const TSharedPtr<FJsonObject>& State)
{
    if (!State || !HasAuthority()) return;
    double Value=0;
    if (State->TryGetNumberField(TEXT("health"),Value)) AbilitySystem->SetNumericAttributeBase(UWarAttributeSet::GetHealthAttribute(),FMath::Clamp(float(Value),1.f,Attributes->GetMaxHealth()));
    if (State->TryGetNumberField(TEXT("mana"),Value)) AbilitySystem->SetNumericAttributeBase(UWarAttributeSet::GetManaAttribute(),FMath::Clamp(float(Value),0.f,Attributes->GetMaxMana()));
    const TSharedPtr<FJsonObject>* Abilities=nullptr;
    if (State->TryGetObjectField(TEXT("abilities"),Abilities)) ClassAbilities->RestoreScenarioState(*Abilities);
    const auto Read=[&](const FString& Name,TSet<FGuid>& Receipts) {
        const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
        if (State->TryGetArrayField(Name,Values)) { Receipts.Reset();for (const auto& Value:*Values) { FGuid Id;if (FGuid::Parse(Value->AsString(),Id)) Receipts.Add(Id); } }
    };
    Read(TEXT("rewards"),RewardReceipts);Read(TEXT("questKills"),QuestKillReceipts);ForceNetUpdate();
}
