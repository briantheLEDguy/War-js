#include "WarAbilityWorkshopDocument.h"
#include "WarAbilityConditions.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

namespace WarWorkshopJson
{
    FString Text(const TSharedPtr<const FJsonObject>& J,const TCHAR* Key)
    { FString V; if (J) J->TryGetStringField(Key,V); return V; }
    double Number(const TSharedPtr<const FJsonObject>& J,const TCHAR* Key,double Default)
    { double V; return J && J->TryGetNumberField(Key,V) ? V : Default; }
    TSharedPtr<FJsonObject> Object(const TSharedPtr<const FJsonObject>& J,const TCHAR* Key)
    { const TSharedPtr<FJsonObject>* V; return J && J->TryGetObjectField(Key,V) ? *V : nullptr; }
    const TArray<TSharedPtr<FJsonValue>>& Array(const TSharedPtr<const FJsonObject>& J,const TCHAR* Key)
    { static const TArray<TSharedPtr<FJsonValue>> Empty; const TArray<TSharedPtr<FJsonValue>>* V; return J && J->TryGetArrayField(Key,V) ? *V : Empty; }
    FString Serialize(const TSharedPtr<const FJsonObject>& J)
    { FString Result; if (J) FJsonSerializer::Serialize(MakeShared<FJsonObject>(*J),TJsonWriterFactory<TCHAR,TCondensedJsonPrintPolicy<TCHAR>>::Create(&Result)); return Result; }
    TSharedPtr<FJsonObject> Parse(const FString& Json)
    { TSharedPtr<FJsonObject> Result; if (Json.Len()<=8000000) FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Result); return Result; }
    TSharedPtr<FJsonObject> Clone(const TSharedPtr<const FJsonObject>& J) { return Parse(Serialize(J)); }
    TSharedPtr<FJsonObject> Find(const TSharedPtr<const FJsonObject>& J,const TCHAR* Collection,const FString& Id)
    { for (const auto& Value : Array(J,Collection)) { const auto Row=Value->AsObject(); if (Text(Row,TEXT("id"))==Id) return Row; } return nullptr; }
    bool Numeric(const TSharedPtr<FJsonObject>& Ability,const FString& Path,double& Value,bool bWrite)
    {
        TArray<FString> Parts; Path.ParseIntoArray(Parts,TEXT("/")); TSharedPtr<FJsonObject> Target; FString Key;
        const TMap<FString,TArray<FString>> Allowed{
            {TEXT("targeting"),{TEXT("range"),TEXT("radius"),TEXT("projectileSpeed"),TEXT("maxTargets")}},
            {TEXT("resource"),{TEXT("manaCost"),TEXT("careerBuild"),TEXT("careerCost"),TEXT("minCareer")}},
            {TEXT("timing"),{TEXT("castSec"),TEXT("channelSec"),TEXT("intervalSec")}},
            {TEXT("amount"),{TEXT("min"),TEXT("max"),TEXT("statScale"),TEXT("levelScale"),TEXT("resourceScale")}},
            {TEXT("periodic"),{TEXT("durationSec"),TEXT("intervalSec")}},
            {TEXT("status"),{TEXT("durationSec"),TEXT("magnitude")}},
            {TEXT("playerStatus"),{TEXT("durationSec"),TEXT("magnitude")}},
            {TEXT("movement"),{TEXT("distance")}}};
        if (Parts.Num()==1 && (Path==TEXT("cooldownSec") || Path==TEXT("gcdSec"))) { Target=Ability; Key=Path; }
        else if (Parts.Num()==2 && (Parts[0]==TEXT("targeting") || Parts[0]==TEXT("resource") || Parts[0]==TEXT("timing")) && Allowed.FindChecked(Parts[0]).Contains(Parts[1]))
        { Target=Object(Ability,*Parts[0]); Key=Parts[1]; }
        else if (Parts.Num()==4 && Parts[0]==TEXT("effects") && Allowed.Contains(Parts[2]) && Allowed.FindChecked(Parts[2]).Contains(Parts[3]))
        { Target=Object(Find(Ability,TEXT("effects"),Parts[1]),*Parts[2]); Key=Parts[3]; }
        else if (Parts.Num()==5 && Parts[0]==TEXT("conditions") && Parts[2]==TEXT("modifiers") && (Parts[4]==TEXT("flat") || Parts[4]==TEXT("percent")))
        {
            for (const auto& Action : Array(Find(Ability,TEXT("conditions"),Parts[1]),TEXT("actions")))
                if (Text(Action->AsObject(),TEXT("kind"))==Parts[4] && Text(Action->AsObject(),TEXT("effectId"))==Parts[3]) { Target=Action->AsObject(); Key=TEXT("value"); break; }
        }
        if (!Target) return false;
        if (bWrite) { if (!FMath::IsFinite(Value)) return false; Target->SetNumberField(Key,Value); if (Path.StartsWith(TEXT("timing/"))) Ability->SetBoolField(TEXT("authoredTiming"),true); return true; }
        return Target->TryGetNumberField(Key,Value);
    }
}

using namespace WarWorkshopJson;

TSharedPtr<FJsonObject> FWarAbilityWorkshopDocument::Merge(const TSharedPtr<FJsonObject>& Base,const TSharedPtr<FJsonObject>& Current,const TSharedPtr<FJsonObject>& Yours,
    const TMap<FString,bool>& UseYours,TArray<FWarWorkshopConflict>& Conflicts)
{
    Conflicts.Reset();
    const auto Equal=[](const TSharedPtr<FJsonValue>& A,const TSharedPtr<FJsonValue>& B) { return A && B ? FJsonValue::CompareEqual(*A,*B) : A==B; };
    TFunction<TSharedPtr<FJsonValue>(TSharedPtr<FJsonValue>,TSharedPtr<FJsonValue>,TSharedPtr<FJsonValue>,FString)> Reconcile;
    Reconcile=[&](TSharedPtr<FJsonValue> B,TSharedPtr<FJsonValue> C,TSharedPtr<FJsonValue> Y,FString Path) -> TSharedPtr<FJsonValue> {
        if (Equal(C,Y) || Equal(B,Y)) return C; if (Equal(B,C)) return Y;
        if (B && C && Y && B->Type==EJson::Object && C->Type==EJson::Object && Y->Type==EJson::Object)
        {
            auto Result=MakeShared<FJsonObject>(); TSet<FString> Keys;
            for (const auto& V:{B,C,Y}) for (const auto& Pair:V->AsObject()->Values) Keys.Add(FString(Pair.Key));
            for (const FString& Key:Keys) { const auto V=Reconcile(B->AsObject()->TryGetField(Key),C->AsObject()->TryGetField(Key),Y->AsObject()->TryGetField(Key),Path+TEXT("/")+Key); if (V) Result->SetField(Key,V); }
            return MakeShared<FJsonValueObject>(Result);
        }
        if (B && C && Y && B->Type==EJson::Array && C->Type==EJson::Array && Y->Type==EJson::Array)
        {
            // Stable-ID collections merge by identity. Predicate arrays remain atomic ordered structures.
            TMap<FString,TSharedPtr<FJsonValue>> Maps[3]; TArray<FString> Orders[3]; bool Identified=true; int32 I=0;
            for (const auto& V:{B,C,Y}) { for (const auto& Entry:V->AsArray()) {
                if (Entry->Type!=EJson::Object) { Identified=false; break; } const auto O=Entry->AsObject(); FString Id=Text(O,TEXT("id")); if (Id.IsEmpty()) Id=Text(O,TEXT("path"));
                if (Id.IsEmpty() || Maps[I].Contains(Id)) { Identified=false; break; } Maps[I].Add(Id,Entry); Orders[I].Add(Id); } ++I; }
            if (Identified)
            {
                TArray<FString> Order=Orders[1]; if (Orders[1]==Orders[0]) Order=Orders[2];
                TArray<FString> Common[3];
                for (int32 J=0;J<3;++J) for (const auto& Id:Orders[J]) if (Maps[0].Contains(Id) && Maps[1].Contains(Id) && Maps[2].Contains(Id)) Common[J].Add(Id);
                if (Common[1]!=Common[0] && Common[2]!=Common[0] && Common[1]!=Common[2])
                {
                    const FString OrderPath=Path+TEXT("/@order");
                    if (const bool* Choice=UseYours.Find(OrderPath)) Order=*Choice ? Orders[2] : Orders[1];
                    else { TSharedPtr<FJsonValue> Values[3]; for (int32 J=0;J<3;++J) { TArray<TSharedPtr<FJsonValue>> Ids; for (const auto& Id:Orders[J]) Ids.Add(MakeShared<FJsonValueString>(Id)); Values[J]=MakeShared<FJsonValueArray>(Ids); } Conflicts.Add({OrderPath,Values[0],Values[1],Values[2]}); }
                }
                else if (Common[1]==Common[0] && Common[2]!=Common[0]) Order=Orders[2];
                for (const FString& Id:Orders[2]) Order.AddUnique(Id); for (const FString& Id:Orders[0]) Order.AddUnique(Id);
                TArray<TSharedPtr<FJsonValue>> Values;
                for (const FString& Id:Order) { const auto V=Reconcile(Maps[0].FindRef(Id),Maps[1].FindRef(Id),Maps[2].FindRef(Id),Path+TEXT("/")+Id); if (V) Values.Add(V); }
                return MakeShared<FJsonValueArray>(Values);
            }
        }
        if (const bool* Choice=UseYours.Find(Path)) return *Choice ? Y : C;
        Conflicts.Add({Path,B,C,Y}); return C;
    };
    if (!Base || !Current || !Yours) return nullptr;
    auto Result=Reconcile(MakeShared<FJsonValueObject>(Base),MakeShared<FJsonValueObject>(Current),MakeShared<FJsonValueObject>(Yours),TEXT(""))->AsObject();
    Result->SetNumberField(TEXT("revision"),Number(Current,TEXT("revision"))); return Clone(Result);
}

bool FWarAbilityWorkshopDocument::Baseline(const TSharedPtr<const FJsonObject>& Manifest,FString& Error)
{
    auto Root=Clone(Object(Object(Manifest,TEXT("abilities")),TEXT("workshop")));
    if (!Root) { Error=TEXT("Ability workshop baseline is missing. Re-export and stage the current content catalog."); return false; }
    Root->SetStringField(TEXT("id"),FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower));
    const auto Source=Object(Manifest,TEXT("source"));
    Root->SetStringField(TEXT("buildId"),Text(Source,TEXT("repositoryRevision")));
    Root->SetStringField(TEXT("contentId"),Text(Source,TEXT("contentSha256")));
    return Load(Serialize(Root),Error);
}
bool FWarAbilityWorkshopDocument::Load(const FString& Json,FString& Error)
{
    const auto Candidate=Parse(Json); TArray<FWarAbilityDefinition> Definitions;
    if (!Compile(Candidate,Definitions,Error)) return false;
    Current=Candidate; Past.Reset(); Future.Reset(); ++ChangeSerial; return true;
}
bool FWarAbilityWorkshopDocument::Commit(const TSharedPtr<FJsonObject>& Candidate,FString& Error)
{
    TArray<FWarAbilityDefinition> Definitions;
    if (!Compile(Candidate,Definitions,Error)) return false;
    if (Current) Past.Add(Serialize(Current)); if (Past.Num()>100) Past.RemoveAt(0);
    Current=Clone(Candidate); Future.Reset(); ++ChangeSerial; return true;
}
bool FWarAbilityWorkshopDocument::Undo()
{ if (Past.IsEmpty()) return false; Future.Add(Serialize(Current)); const double Revision=Number(Current,TEXT("revision")); Current=Parse(Past.Pop()); Current->SetNumberField(TEXT("revision"),Revision); ++ChangeSerial; return true; }
bool FWarAbilityWorkshopDocument::Redo()
{ if (Future.IsEmpty()) return false; Past.Add(Serialize(Current)); const double Revision=Number(Current,TEXT("revision")); Current=Parse(Future.Pop()); Current->SetNumberField(TEXT("revision"),Revision); ++ChangeSerial; return true; }
void FWarAbilityWorkshopDocument::AcknowledgeRevision(int64 Revision)
{ if (Current) Current->SetNumberField(TEXT("revision"),Revision); }

TSharedPtr<FJsonObject> FWarAbilityWorkshopDocument::Effective(const TSharedPtr<const FJsonObject>& Workspace,const TSharedPtr<const FJsonObject>& Assignment,FString& Error)
{
    auto Ability=Clone(Find(Workspace,TEXT("abilities"),Text(Assignment,TEXT("abilityId"))));
    if (!Ability) { Error=TEXT("Assigned ability no longer exists."); return nullptr; }
    TSet<FString> Paths;
    for (const auto& Entry : Array(Assignment,TEXT("overrides")))
    {
        const auto Override=Entry->AsObject(); const FString Path=Text(Override,TEXT("path")); double Value=Number(Override,TEXT("value"),NAN);
        if (Paths.Contains(Path) || !Numeric(Ability,Path,Value,true)) { Error=TEXT("Invalid or duplicate override: ")+Path; return nullptr; }
        Paths.Add(Path);
    }
    return Ability;
}
bool FWarAbilityWorkshopDocument::EditCells(const TArray<FWarWorkshopCellEdit>& Edits,const TSet<FString>& VisibleSelected,FString& Error)
{
    auto Candidate=Clone(Current);
    TMap<FString,TSet<FString>> Cells;
    for (const auto& Edit : Edits)
    {
        auto& Fields=Cells.FindOrAdd(Edit.AssignmentId); if (Fields.Contains(Edit.Path)) { Error=TEXT("Selection repeats the same assignment field."); return false; } Fields.Add(Edit.Path);
        if (!TArray<FString>{TEXT("set"),TEXT("add"),TEXT("multiply"),TEXT("reset")}.Contains(Edit.Operation)) { Error=TEXT("Unsupported edit operation."); return false; }
        if (!VisibleSelected.Contains(Edit.AssignmentId)) { Error=TEXT("Bulk edits cannot include hidden/unselected rows."); return false; }
        const auto Assignment=Find(Candidate,TEXT("assignments"),Edit.AssignmentId);
        auto Ability=Effective(Candidate,Assignment,Error); if (!Assignment || !Ability) return false;
        auto Overrides=Array(Assignment,TEXT("overrides"));
        Overrides.RemoveAll([&](const auto& V) { return Text(V->AsObject(),TEXT("path"))==Edit.Path; });
        if (Edit.Operation!=TEXT("reset"))
        {
            double Previous=0; const bool Present=Numeric(Ability,Edit.Path,Previous); double Value=Edit.Value;
            if (!Present && Edit.Operation!=TEXT("set")) { Error=TEXT("Arithmetic requires an existing numeric value."); return false; }
            if (Edit.Operation==TEXT("add")) Value+=Previous; else if (Edit.Operation==TEXT("multiply")) Value*=Previous;
            if (!Numeric(Ability,Edit.Path,Value,true)) { Error=TEXT("Invalid numeric field: ")+Edit.Path; return false; }
            auto Override=MakeShared<FJsonObject>(); Override->SetStringField(TEXT("path"),Edit.Path); Override->SetNumberField(TEXT("value"),Value); Overrides.Add(MakeShared<FJsonValueObject>(Override));
        }
        Assignment->SetArrayField(TEXT("overrides"),Overrides);
    }
    return Commit(Candidate,Error);
}
bool FWarAbilityWorkshopDocument::Compile(const TSharedPtr<const FJsonObject>& Workspace,TArray<FWarAbilityDefinition>& Out,FString& Error,TArray<FWarAbilityDefinition>* Library)
{
    Out.Reset(); Error.Reset();
    const auto Fail=[&](const FString& Message) { Out.Reset(); Error=Message; return false; };
    if (!Workspace || Number(Workspace,TEXT("schemaVersion"))!=1 || Text(Workspace,TEXT("id")).IsEmpty() || Number(Workspace,TEXT("revision"),-1)<0)
        return Fail(TEXT("Invalid workshop schema, identity, or revision."));
    const auto& Classes=Array(Workspace,TEXT("classes")); const auto& Abilities=Array(Workspace,TEXT("abilities")); const auto& Assignments=Array(Workspace,TEXT("assignments"));
    if (Classes.Num()!=24 || Abilities.Num()>5000 || Assignments.Num()>10000) return Fail(TEXT("A bounded catalog and all 24 campaign classes are required."));
    TSet<FString> Ids; TArray<FWarAbilityDefinition> References;
    const auto ValidateFields=[&](const TSharedPtr<FJsonObject>& A) {
        const auto Bounded=[](const TSharedPtr<FJsonObject>& J,const TCHAR* Key,double Min,double Max,bool Required=false) {
            if (!Required && J && !J->HasField(Key)) return true; const double V=Number(J,Key,NAN); return FMath::IsFinite(V) && V>=Min && V<=Max; };
        if (!Bounded(A,TEXT("cooldownSec"),0,3600,true) || !Bounded(A,TEXT("gcdSec"),0,60,true)) return false;
        const auto T=Object(A,TEXT("targeting")),R=Object(A,TEXT("resource")),Timing=Object(A,TEXT("timing"));
        if (!T || !R || !Timing || !Object(A,TEXT("visual")) || !Bounded(Object(A,TEXT("animation")),TEXT("durationSec"),.01,120,true)) return false;
        if (!TArray<FString>{TEXT("self"),TEXT("enemy"),TEXT("ally"),TEXT("ground")}.Contains(Text(T,TEXT("target")))
            || !TArray<FString>{TEXT("melee"),TEXT("projectile"),TEXT("beam"),TEXT("cone"),TEXT("area"),TEXT("self"),TEXT("dash"),TEXT("deployable"),TEXT("pet")}.Contains(Text(T,TEXT("shape")))
            || !Bounded(T,TEXT("range"),0,200,true) || !Bounded(T,TEXT("radius"),0,100) || !Bounded(T,TEXT("projectileSpeed"),.1,1000) || !Bounded(T,TEXT("maxTargets"),1,128)) return false;
        if (T->HasField(TEXT("maxTargets")) && Number(T,TEXT("maxTargets"))!=FMath::FloorToDouble(Number(T,TEXT("maxTargets")))) return false;
        for (const TCHAR* K:{TEXT("manaCost"),TEXT("careerCost"),TEXT("careerBuild"),TEXT("minCareer")}) if (!Bounded(R,K,0,10000)) return false;
        if (!TArray<FString>{TEXT("instant"),TEXT("cast"),TEXT("channel")}.Contains(Text(Timing,TEXT("mode"))) || !Bounded(Timing,TEXT("castSec"),0,60,true)) return false;
        if (Text(Timing,TEXT("mode"))==TEXT("channel") && (!Bounded(Timing,TEXT("channelSec"),.1,60,true) || !Bounded(Timing,TEXT("intervalSec"),.1,Number(Timing,TEXT("channelSec")),true))) return false;
        if (!A->HasTypedField<EJson::Boolean>(TEXT("archived")) || !A->HasTypedField<EJson::Array>(TEXT("effects")) || !A->HasTypedField<EJson::Array>(TEXT("conditions"))) return false;
        return !Array(A,TEXT("effects")).IsEmpty() || !Text(A,TEXT("unavailableReason")).IsEmpty();
    };
    for (const auto& Value : Abilities)
    {
        const auto A=Value->AsObject(); const FString Id=Text(A,TEXT("id"));
        if (Id.IsEmpty() || Ids.Contains(Id) || Text(A,TEXT("name")).TrimStartAndEnd().IsEmpty() || Text(A,TEXT("name")).Len()>100) return Fail(TEXT("Ability names and unique identities are required."));
        Ids.Add(Id);
        if (!ValidateFields(A)) return Fail(TEXT("Invalid targeting, resource, timing, presentation, or effects in ")+Id);
        FWarAbilityDefinition Reference; Reference.Id=FName(*Id); Reference.Name=Text(A,TEXT("name")); Reference.Shape=FName(*Text(Object(A,TEXT("targeting")),TEXT("shape"))); Reference.TimingMode=FName(*Text(Object(A,TEXT("timing")),TEXT("mode")));
        if (!WarAbilityConditions::ParseRules(A,Reference.Conditions,Error)) return false;
        for (const TCHAR* Field : {TEXT("cooldownSec"),TEXT("gcdSec")})
        { const double V=Number(A,Field,-1); if (!FMath::IsFinite(V) || V<0 || V>(FString(Field)==TEXT("gcdSec") ? 60 : 3600)) return Fail(TEXT("Invalid ability cooldown.")); }
        TSet<FName> Effects;
        if (Array(A,TEXT("effects")).Num()>32) return Fail(TEXT("At most 32 effects per ability."));
        for (const auto& Entry : Array(A,TEXT("effects")))
        { FWarAbilityEffect E; if (!WarAbilityConditions::ParseEffect(Entry->AsObject(),E,Error)) return false; if (Effects.Contains(E.Id)) return Fail(TEXT("Duplicate effect identity.")); Effects.Add(E.Id);
          if (E.Kind==TEXT("wrath_relic") && Id!=TEXT("battle_prelate.icon_of_wrath")) return Fail(TEXT("New relic authoring is not admitted.")); Reference.Effects.Add(E); }
        const auto Target=Object(A,TEXT("targeting"));
        if (!Target || Number(Target,TEXT("range"),-1)<0 || Number(Target,TEXT("range"))>200 || Number(Target,TEXT("radius"))>100)
            return Fail(TEXT("Target range/radius exceeds admitted limits."));
        References.Add(MoveTemp(Reference));
    }
    for (const auto& A:References) if (!WarAbilityConditions::Validate(A,References,Error)) return Fail(A.Name+TEXT(": ")+Error);
    TArray<TSharedPtr<FJsonValue>> Kits,Progression;
    TSet<FString> AssignmentIds,Pairs,KnownClasses;
    const TMap<FString,TArray<FString>> Roster{
        {TEXT("empire"),{TEXT("Ember Arcanist"),TEXT("Hex Inquisitor"),TEXT("Sunfire Templar"),TEXT("Battle Prelate")}},
        {TEXT("dwarf"),{TEXT("Stoneguard"),TEXT("Doomseeker"),TEXT("Glyphbinder"),TEXT("Siegewright")}},
        {TEXT("high_elf"),{TEXT("Blade Savant"),TEXT("Pride Warden"),TEXT("Aether Sage"),TEXT("Veil Ranger")}},
        {TEXT("chaos"),{TEXT("Dreadsworn"),TEXT("Warped Reaver"),TEXT("Void Magister"),TEXT("Ruin Oracle")}},
        {TEXT("greenskin"),{TEXT("Warbrute"),TEXT("Fang Herder"),TEXT("Bog Hexer"),TEXT("Cleaver")}},
        {TEXT("dark_elf"),{TEXT("Blood Dancer"),TEXT("Dread Guard"),TEXT("Dusk Weaver"),TEXT("Crimson Acolyte")}}};
    for (const auto& ClassValue : Classes)
    {
        const auto Career=ClassValue->AsObject(); const FString CareerId=Text(Career,TEXT("id"));
        if (CareerId.IsEmpty() || KnownClasses.Contains(CareerId)) return Fail(TEXT("Duplicate class identity.")); KnownClasses.Add(CareerId);
        const FString Race=Text(Career,TEXT("race")),Name=Text(Career,TEXT("name"));
        const FString Realm=TArray<FString>{TEXT("empire"),TEXT("dwarf"),TEXT("high_elf")}.Contains(Race) ? TEXT("aegis") : TEXT("riftbound");
        if (!Roster.Contains(Race) || !Roster.FindChecked(Race).Contains(Name) || CareerId!=Name.ToLower().Replace(TEXT(" "),TEXT("_")) || Text(Career,TEXT("realm"))!=Realm)
            return Fail(TEXT("Campaign class names, identities, race and realm cannot be changed."));
        auto Kit=MakeShared<FJsonObject>(); Kit->SetStringField(TEXT("career"),Text(Career,TEXT("name"))); Kit->SetObjectField(TEXT("resource"),Clone(Object(Career,TEXT("resource"))));
        TArray<TSharedPtr<FJsonValue>> Rows;
        for (const auto& AssignmentValue : Assignments)
        {
            const auto Assignment=AssignmentValue->AsObject(); if (Text(Assignment,TEXT("classId"))!=CareerId) continue;
            const FString AssignmentId=Text(Assignment,TEXT("id")), AbilityId=Text(Assignment,TEXT("abilityId")), Pair=CareerId+TEXT(":")+AbilityId;
            if (AssignmentId.IsEmpty() || AssignmentIds.Contains(AssignmentId) || Pairs.Contains(Pair)) return Fail(TEXT("Duplicate assignment or class/ability pair."));
            AssignmentIds.Add(AssignmentId); Pairs.Add(Pair);
            auto A=Effective(Workspace,Assignment,Error); if (!A) return false;
            if (!ValidateFields(A)) return Fail(TEXT("Invalid effective fields in assignment ")+AssignmentId);
            if (!Object(Assignment,TEXT("presentations")) || !Assignment->HasTypedField<EJson::Array>(TEXT("overrides")) || Array(Assignment,TEXT("overrides")).Num()>256)
                return Fail(TEXT("Invalid assignment bindings or overrides."));
            bool Archived=false; A->TryGetBoolField(TEXT("archived"),Archived); if (Archived) continue;
            const double Unlock=Number(Assignment,TEXT("unlockLevel"));
            if (Unlock<1 || Unlock>45 || Unlock!=FMath::FloorToDouble(Unlock)) return Fail(TEXT("Unlock level must be an integer from 1 to 45."));
            const double Order=Number(Assignment,TEXT("displayOrder"),-1);
            if (Order<0 || Order>10000 || Order!=FMath::FloorToDouble(Order)) return Fail(TEXT("Display order must be an integer from 0 to 10000."));
            const auto Resource=Object(A,TEXT("resource")); const double Max=Number(Object(Career,TEXT("resource")),TEXT("max"));
            if (Number(Resource,TEXT("careerCost"))>Max || Number(Resource,TEXT("minCareer"))>Max) return Fail(TEXT("Ability resource requirement exceeds the class maximum."));
            for (const TCHAR* Field : {TEXT("cooldownSec"),TEXT("gcdSec")}) if (Number(A,Field,-1)<0 || Number(A,Field)>3600) return Fail(TEXT("Invalid effective cooldown."));
            for (const auto& EffectValue : Array(A,TEXT("effects"))) { FWarAbilityEffect E; if (!WarAbilityConditions::ParseEffect(EffectValue->AsObject(),E,Error)) return false; }
            A->SetStringField(TEXT("runtimeCareer"),CareerId); A->SetStringField(TEXT("assignmentId"),AssignmentId);
            A->SetNumberField(TEXT("slot"),Number(Assignment,TEXT("displayOrder"))); A->SetNumberField(TEXT("unlockLevel"),Unlock);
            A->SetObjectField(TEXT("presentations"),Clone(Object(Assignment,TEXT("presentations"))));
            Rows.Add(MakeShared<FJsonValueObject>(A));
        }
        Kit->SetArrayField(TEXT("abilities"),Rows); Kits.Add(MakeShared<FJsonValueObject>(Kit));
    }
    if (AssignmentIds.Num()!=Assignments.Num()) return Fail(TEXT("Assignment references an unknown class."));
    auto Source=MakeShared<FJsonObject>(); Source->SetArrayField(TEXT("kits"),Kits); Source->SetArrayField(TEXT("progression"),Progression);
    auto Manifest=MakeShared<FJsonObject>(); Manifest->SetObjectField(TEXT("abilities"),Source);
    if (!WarAbilities::Parse(Manifest,Out,Error,true)) return false;
    for (const auto& A : Out) if (!WarAbilityConditions::Validate(A,References,Error)) return Fail(A.Name+TEXT(": ")+Error);
    if (Library) *Library=MoveTemp(References);
    return true;
}
